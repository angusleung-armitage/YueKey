// SPDX-License-Identifier: MIT
// GDBus callbacks only queue data. Rime commits happen in ProcessKeyEvent.
#include "gesture.h"
#include <gio/gio.h>
#include <rime_api.h>
#include <rime/config.h>
#include <rime/context.h>
#include <rime/engine.h>
#include <rime/key_event.h>
#include <rime/processor.h>
#include <rime/registry.h>
#include <rime/schema.h>
#include <map>
#include <mutex>
#include <string>

namespace {
constexpr auto kController = "org.quick_hk.Dictation";
constexpr auto kPath = "/org/quick_hk/Dictation";
constexpr auto kBridge = "org.quick_hk.RimeDictation";
constexpr auto kBridgePath = "/org/quick_hk/RimeDictation";
constexpr int kWakeKey = 0xffe4;  // Right Ctrl: a modifier present in normal XKB maps
struct Request { std::string text; gint64 ready_at = 0; };
std::mutex requests_mutex;
std::map<std::string, Request> requests;
GDBusConnection* bus = nullptr;
guint registration = 0, owner = 0;

void Call(const char* method, const std::string& id) {
  if (bus) g_dbus_connection_call(bus, kController, kPath, kController, method,
      g_variant_new("(s)", id.c_str()), nullptr, G_DBUS_CALL_FLAGS_NONE,
      2000, nullptr, nullptr, nullptr);
}

void Method(GDBusConnection* connection, const gchar* sender, const gchar*,
            const gchar*, const gchar* method, GVariant* args,
            GDBusMethodInvocation* invocation, gpointer) {
  // Only the currently owning controller can supply a recognition result.
  GVariant* reply = g_dbus_connection_call_sync(connection,
      "org.freedesktop.DBus", "/org/freedesktop/DBus", "org.freedesktop.DBus",
      "GetNameOwner", g_variant_new("(s)", kController), G_VARIANT_TYPE("(s)"),
      G_DBUS_CALL_FLAGS_NONE, 500, nullptr, nullptr);
  const gchar* controller = nullptr;
  if (reply) g_variant_get(reply, "(&s)", &controller);
  bool authorized = controller && g_str_equal(controller, sender);
  if (reply) g_variant_unref(reply);
  if (!authorized) {
    g_dbus_method_invocation_return_dbus_error(invocation,
        "org.quick_hk.Error.Unauthorized", "Dictation controller required");
    return;
  }
  const gchar *id = nullptr, *text = nullptr;
  bool accepted = false;
  {
    std::lock_guard<std::mutex> lock(requests_mutex);
    if (g_str_equal(method, "QueueResult")) {
      g_variant_get(args, "(&s&s)", &id, &text);
      auto it = requests.find(id);
      if (it != requests.end() && it->second.ready_at == 0 &&
          text && *text && strlen(text) <= 65536) {
        it->second = {text, g_get_monotonic_time()};
        accepted = true;
      }
    } else if (g_str_equal(method, "Cancel")) {
      g_variant_get(args, "(&s)", &id);
      accepted = requests.erase(id) != 0;
    }
  }
  g_dbus_method_invocation_return_value(invocation, g_variant_new("(b)", accepted));
}

void EnsureBus() {
  if (bus) return;
  bus = g_bus_get_sync(G_BUS_TYPE_SESSION, nullptr, nullptr);
  if (!bus) return;
  constexpr auto xml = R"(<node><interface name="org.quick_hk.RimeDictation">
    <method name="QueueResult"><arg type="s" direction="in"/><arg type="s" direction="in"/><arg type="b" direction="out"/></method>
    <method name="Cancel"><arg type="s" direction="in"/><arg type="b" direction="out"/></method>
  </interface></node>)";
  auto* info = g_dbus_node_info_new_for_xml(xml, nullptr);
  static const GDBusInterfaceVTable table = {Method, nullptr, nullptr, {nullptr}};
  registration = g_dbus_connection_register_object(bus, kBridgePath,
      info->interfaces[0], &table, nullptr, nullptr, nullptr);
  g_dbus_node_info_unref(info);
  owner = g_bus_own_name_on_connection(bus, kBridge, G_BUS_NAME_OWNER_FLAGS_NONE,
                                     nullptr, nullptr, nullptr, nullptr);
}

class Dictation : public rime::Processor {
 public:
  explicit Dictation(const rime::Ticket& ticket) : Processor(ticket) {
    auto* config = engine_->schema()->config();
    std::string key;
    config->GetBool("quick_hk/dictation_enabled", &enabled_);
    config->GetString("quick_hk/dictation_key", &key);
    gesture_ = quick_hk::DoubleControl(key == "Control_R" ? 0xffe4 : 0xffe3);
    // IBus Reset/ClearComposition also fires this when moving between fields.
    update_ = engine_->context()->update_notifier().connect(
        [this](rime::Context*) { Cancel(); gesture_.Reset(); });
    if (enabled_) EnsureBus();
  }
  ~Dictation() override { update_.disconnect(); Cancel(); }

  rime::ProcessResult ProcessKeyEvent(const rime::KeyEvent& key) override {
    auto* ctx = engine_->context();
    if (!id_.empty()) {
      std::lock_guard<std::mutex> lock(requests_mutex);
      if (!requests.count(id_)) id_.clear();
    }
    if (!enabled_ || ctx->get_option("ascii_mode")) {
      gesture_.Reset(); Cancel(); return rime::kNoop;
    }
    if (key.keycode() == kWakeKey && !key.release()) {
      std::string text;
      {
        std::lock_guard<std::mutex> lock(requests_mutex);
        auto it = requests.find(id_);
        if (it != requests.end() && it->second.ready_at &&
            g_get_monotonic_time() - it->second.ready_at < 5000000 &&
            ctx->input().empty() && !key.release()) {
          text = std::move(it->second.text);
          requests.erase(it);
        }
      }
      if (!text.empty()) {
        const auto committed_id = id_;
        id_.clear(); ctx->Clear(); engine_->CommitText(text);
        Call("Committed", committed_id);
        return rime::kAccepted;
      }
    }
    const bool control = key.keycode() == 0xffe3 || key.keycode() == 0xffe4;
    if (!key.release() && !control && !id_.empty()) {
      Cancel(); gesture_.Reset();
      if (key.keycode() == 0xff1b) return rime::kAccepted;
    }
    if (!ctx->input().empty()) { gesture_.Reset(); return rime::kNoop; }
    if (!gesture_.Feed(key.keycode(), key.release(),
          key.shift() || key.alt() || key.super(), g_get_monotonic_time() / 1000))
      return rime::kNoop;
    if (!bus) return rime::kNoop;
    if (id_.empty()) {
      gchar* uuid = g_uuid_string_random(); id_ = uuid; g_free(uuid);
      std::lock_guard<std::mutex> lock(requests_mutex);
      requests.emplace(id_, Request{});
    }
    Call("Toggle", id_);
    return rime::kAccepted;
  }
 private:
  void Cancel() {
    if (id_.empty()) return;
    Call("Cancel", id_);
    std::lock_guard<std::mutex> lock(requests_mutex);
    requests.erase(id_); id_.clear();
  }
  bool enabled_ = false;
  std::string id_;
  quick_hk::DoubleControl gesture_;
  rime::connection update_;
};
}  // namespace

static void rime_quick_hk_dictation_initialize() {
  rime::Registry::instance().Register("quick_hk_dictation",
      new rime::Component<Dictation>());
}
static void rime_quick_hk_dictation_finalize() {
  if (owner) g_bus_unown_name(owner);
  if (registration && bus) g_dbus_connection_unregister_object(bus, registration);
  if (bus) g_object_unref(bus);
  bus = nullptr; registration = owner = 0;
  std::lock_guard<std::mutex> lock(requests_mutex); requests.clear();
}
RIME_REGISTER_MODULE(quick_hk_dictation)

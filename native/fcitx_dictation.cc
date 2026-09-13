// SPDX-License-Identifier: MIT
// All focus checks and commits run on Fcitx's event loop, including D-Bus calls.
#include "gesture.h"
#include <dbus_public.h>
#include <fcitx/addonfactory.h>
#include <fcitx/addonmanager.h>
#include <fcitx/inputcontext.h>
#include <fcitx/inputmethodengine.h>
#include <fcitx/inputmethodentry.h>
#include <fcitx/inputpanel.h>
#include <fcitx/instance.h>
#include <fcitx-utils/dbus/objectvtable.h>
#include <fcitx-utils/dbus/servicewatcher.h>
#include <fcitx-utils/utf8.h>
#include <glib.h>
#include <algorithm>
#include <iomanip>
#include <sstream>
#include <stdexcept>
#include <utility>
#include <vector>

namespace {
constexpr auto kController = "org.quick_hk.Dictation";
constexpr auto kControllerPath = "/org/quick_hk/Dictation";
constexpr auto kBridge = "org.quick_hk.FcitxDictation";
constexpr auto kBridgePath = "/org/quick_hk/FcitxDictation";

class YueKeyDictation : public fcitx::AddonInstance,
                       public fcitx::dbus::ObjectVTable<YueKeyDictation> {
 public:
  explicit YueKeyDictation(fcitx::Instance* instance) : instance_(instance) {
    auto* addon = instance_->addonManager().addon("dbus", true);
    bus_ = addon ? addon->call<fcitx::IDBusModule::bus>() : nullptr;
    if (!bus_ || !bus_->requestName(kBridge, fcitx::dbus::RequestNameFlag::None) ||
        !bus_->addObjectVTable(kBridgePath, kBridge, *this))
      throw std::runtime_error("YueKey Fcitx D-Bus bridge could not start");
    watcher_ = std::make_unique<fcitx::dbus::ServiceWatcher>(*bus_);
    owner_watch_ = watcher_->watchService(kController,
        [this](const auto&, const auto&, const std::string& owner) {
          cancel(); enabled_ = false; controller_ = owner;
        });
    watch(fcitx::EventType::InputContextKeyEvent, [this](fcitx::Event& event) {
      key(static_cast<fcitx::KeyEvent&>(event));
    });
    watch(fcitx::EventType::InputContextFocusIn, [this](fcitx::Event& event) {
      invalidate();
      focused_ = static_cast<fcitx::InputContextEvent&>(event).inputContext()->watch();
    });
    for (auto type : {fcitx::EventType::InputContextFocusOut,
                      fcitx::EventType::InputContextDestroyed,
                      fcitx::EventType::InputContextReset,
                      fcitx::EventType::InputContextCapabilityAboutToChange,
                      fcitx::EventType::InputContextCapabilityChanged,
                      fcitx::EventType::InputContextCursorRectChanged,
                      fcitx::EventType::InputContextSurroundingTextUpdated,
                      fcitx::EventType::InputContextSwitchInputMethod,
                      fcitx::EventType::InputContextInputMethodDeactivated,
                      fcitx::EventType::InputContextInvokeAction,
                      fcitx::EventType::InputContextCommitString}) {
      watch(type, [this, type](fcitx::Event& event) {
        auto* ic = static_cast<fcitx::InputContextEvent&>(event).inputContext();
        if (ic == focused_.get()) {
          invalidate();
          if (type == fcitx::EventType::InputContextFocusOut ||
              type == fcitx::EventType::InputContextDestroyed) focused_.unwatch();
        }
      });
    }
  }
  ~YueKeyDictation() override { cancel(); releaseSlot(); if (bus_) bus_->releaseName(kBridge); }

 private:
  void watch(fcitx::EventType type, fcitx::EventHandler handler) {
    handlers_.push_back(instance_->watchEvent(type, fcitx::EventWatcherPhase::PreInputMethod, std::move(handler)));
  }
  bool authorized() const {
    return !controller_.empty() && currentMessage() && currentMessage()->sender() == controller_;
  }
  bool eligible(fcitx::InputContext* ic) {
    if (!enabled_ || !ic || !ic->hasFocus()) return false;
    auto flags = ic->capabilityFlags();
    if (!flags.test(fcitx::CapabilityFlag::Preedit) ||
        flags.testAny(fcitx::CapabilityFlag::PasswordOrSensitive) ||
        flags.test(fcitx::CapabilityFlag::Disable)) return false;
    // XIM cannot reliably report secure-field flags. GTK/Qt D-Bus and native
    // Wayland frontends carry the flags needed by this bridge.
    if (ic->frontendName() == "xim") return false;
    auto* entry = instance_->inputMethodEntry(ic);
    auto* engine = instance_->inputMethodEngine(ic);
    return entry && engine && entry->uniqueName() == "rime" &&
           engine->subMode(*entry, *ic) == "港式速成" &&
           ic->inputPanel().preedit().empty() && ic->inputPanel().clientPreedit().empty();
  }
  void call(const char* method, const std::string& id) {
    if (controller_.empty()) return;
    auto message = bus_->createMethodCall(controller_.c_str(), kControllerPath, kController, method);
    message << id;
    message.send();
  }
  void clearPanel() {
    if (auto* ic = target_.get()) {
      ic->inputPanel().setAuxUp(fcitx::Text());
      ic->updateUserInterface(fcitx::UserInterfaceComponent::InputPanel);
    }
  }
  void cancel() {
    const auto id = std::exchange(request_, {});
    finishing_ = false;
    clearPanel(); target_.unwatch();
    if (!id.empty()) call("Cancel", id);
  }
  void invalidate() { ++generation_; gesture_.Reset(); cancel(); }
  void key(fcitx::KeyEvent& event) {
    auto* ic = event.inputContext();
    if (ic != focused_.get()) { invalidate(); focused_ = ic->watch(); }
    const auto sym = event.rawKey().sym();
    const bool control = sym == FcitxKey_Control_L || sym == FcitxKey_Control_R;
    if (!event.isRelease() && !control && !request_.empty()) {
      invalidate();
      if (sym == FcitxKey_Escape) event.filterAndAccept();
      return;
    }
    if (!eligible(ic)) { gesture_.Reset(); cancel(); return; }
    const auto states = event.rawKey().states();
    const bool modifiers = states.testAny(fcitx::KeyStates(fcitx::KeyState::Shift) | fcitx::KeyState::Alt | fcitx::KeyState::Super | fcitx::KeyState::Repeat);
    if (!gesture_.Feed(sym, event.isRelease(), modifiers, g_get_monotonic_time() / 1000)) return;
    if (request_.empty()) {
      char* uuid = g_uuid_string_random(); request_ = uuid; g_free(uuid);
      target_ = ic->watch(); target_generation_ = generation_;
      started_ = g_get_monotonic_time();
    } else if (finishing_) return;
    else finishing_ = true;
    call("Toggle", request_);
    event.filterAndAccept();
  }
  bool configure(bool enabled, const std::string& key) {
    if (!authorized() || (key != "Control_L" && key != "Control_R")) return false;
    const int code = key == "Control_R" ? FcitxKey_Control_R : FcitxKey_Control_L;
    if (enabled_ != enabled || key_ != code) {
      invalidate(); enabled_ = enabled; key_ = code; gesture_ = quick_hk::DoubleControl(code);
    }
    return true;
  }
  std::string snapshot() {
    const bool allowed = eligible(focused_.get());
    std::ostringstream uuid;
    if (auto* ic = focused_.get())
      for (unsigned char byte : ic->uuid()) uuid << std::hex << std::setw(2) << std::setfill('0') << int(byte);
    return std::string("{\"allowed\":") + (allowed ? "true" : "false") +
      ",\"context\":\"" + uuid.str() + "\",\"generation\":" + std::to_string(generation_) + ",\"window\":0}";
  }
  bool queueResult(const std::string& id, const std::string& text) {
    auto* ic = target_.get();
    if (!authorized() || !finishing_ || request_.empty() || id != request_ || !eligible(ic) ||
        ic != focused_.get() || generation_ != target_generation_ || text.empty() ||
        text.size() > 65536 || !g_utf8_validate(text.c_str(), text.size(), nullptr) ||
        g_get_monotonic_time() - started_ > 180000000) return false;
    // Consume before reset/commit re-enters event handlers. No wake key and no
    // global keyboard/clipboard injection is involved.
    request_.clear(); clearPanel(); target_.unwatch(); finishing_ = false;
    ic->reset();
    ic->commitString(text);
    return true;
  }
  bool cancelRequest(const std::string& id) {
    if (!authorized() || id != request_) return false;
    cancel(); return true;
  }
  void show(const std::string& state, double level, double elapsed) {
    if (!authorized()) return;
    if (state == "idle") { clearPanel(); return; }
    auto* ic = target_.get();
    if (!ic || !eligible(ic) || target_generation_ != generation_) { cancel(); return; }
    if (state == "finishing") finishing_ = true;
    // The input panel is positioned by Fcitx beside the active caret, including
    // native Wayland clients. Keep the indicator compact like the other desktops.
    std::string label = state == "recording" ? "🎙 " :
                        state == "finishing" ? "🎙 …" : "🎙 ·";
    if (state == "recording") {
      const char* levels[] = {"▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"};
      label += levels[std::min(7, int(std::clamp(level, 0.0, 1.0) * 8))];
    }
    ic->inputPanel().setAuxUp(fcitx::Text(label));
    ic->updateUserInterface(fcitx::UserInterfaceComponent::InputPanel);
  }
  FCITX_OBJECT_VTABLE_METHOD(configure, "Configure", "bs", "b");
  FCITX_OBJECT_VTABLE_METHOD(snapshot, "Snapshot", "", "s");
  FCITX_OBJECT_VTABLE_METHOD(queueResult, "QueueResult", "ss", "b");
  FCITX_OBJECT_VTABLE_METHOD(cancelRequest, "Cancel", "s", "b");
  FCITX_OBJECT_VTABLE_METHOD(show, "Show", "sdd", "");
  fcitx::Instance* instance_;
  fcitx::dbus::Bus* bus_ = nullptr;
  std::unique_ptr<fcitx::dbus::ServiceWatcher> watcher_;
  std::unique_ptr<fcitx::dbus::ServiceWatcherEntry> owner_watch_;
  std::vector<std::unique_ptr<fcitx::HandlerTableEntry<fcitx::EventHandler>>> handlers_;
  fcitx::TrackableObjectReference<fcitx::InputContext> focused_, target_;
  std::string controller_, request_;
  quick_hk::DoubleControl gesture_;
  bool enabled_ = false, finishing_ = false;
  int key_ = FcitxKey_Control_L;
  uint64_t generation_ = 0, target_generation_ = 0;
  gint64 started_ = 0;
};
class Factory : public fcitx::AddonFactory {
 public:
  fcitx::AddonInstance* create(fcitx::AddonManager* manager) override {
    return new YueKeyDictation(manager->instance());
  }
};
} // namespace
FCITX_ADDON_FACTORY(Factory);

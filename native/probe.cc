// Real librime protocol driver for headless acceptance tests; no desktop input.
#include <rime_api.h>
#include <dlfcn.h>
#include <gio/gio.h>
#include <poll.h>
#include <unistd.h>
#include <chrono>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

std::string quote(const char* value) {
  std::string out = "\"";
  if (value) for (unsigned char c : std::string(value)) {
    if (c == '"' || c == '\\') out += '\\';
    if (c == '\n') out += "\\n";
    else if (c == '\r') out += "\\r";
    else if (c == '\t') out += "\\t";
    else if (c < 0x20) out += ' ';
    else out += c;
  }
  return out + "\"";
}

void snapshot(RimeApi* api, RimeSessionId session, bool handled, double elapsed) {
  RIME_STRUCT(RimeCommit, commit);
  const bool committed = api->get_commit(session, &commit);
  std::cout << "{\"handled\":" << (handled ? "true" : "false")
            << ",\"commit\":" << quote(committed ? commit.text : "")
            << ",\"input\":" << quote(api->get_input(session))
            << ",\"elapsed_ms\":" << elapsed;
  RIME_STRUCT(RimeContext, context);
  if (api->get_context(session, &context)) {
    std::cout << ",\"preedit\":" << quote(context.composition.preedit)
              << ",\"page\":" << context.menu.page_no
              << ",\"selected\":" << context.menu.highlighted_candidate_index
              << ",\"candidates\":[";
    for (int i = 0; i < context.menu.num_candidates; ++i) {
      if (i) std::cout << ',';
      std::cout << quote(context.menu.candidates[i].text);
    }
    std::cout << ']';
    api->free_context(&context);
  }
  std::cout << "}\n" << std::flush;
  if (committed) api->free_commit(&commit);
}

int main(int argc, char** argv) {
  if (argc != 4 && argc != 5) {
    std::cerr << "Usage: quick-hk-probe USER_DIR SHARED_DIR PREDICT_PLUGIN [DICTATION_PLUGIN]\n";
    return 2;
  }
  if (!dlopen(argv[3], RTLD_NOW | RTLD_GLOBAL)) {
    std::cerr << dlerror() << '\n';
    return 1;
  }
  if (argc == 5 && !dlopen(argv[4], RTLD_NOW | RTLD_GLOBAL)) {
    std::cerr << dlerror() << '\n'; return 1;
  }
  auto* api = rime_get_api();
  RIME_STRUCT(RimeTraits, traits);
  traits.shared_data_dir = argv[2];
  traits.user_data_dir = argv[1];
  traits.app_name = "quick_hk.probe";
  traits.log_dir = argv[1];
  const char* modules[] = {"default", "plugins", "quick_hk_predict", argc == 5 ? "quick_hk_dictation" : nullptr, nullptr};
  traits.modules = modules;
  api->setup(&traits);
  api->initialize(&traits);
  std::vector<RimeSessionId> sessions;
  auto add_session = [&]() {
    auto session = api->create_session();
    if (!api->select_schema(session, "quick_hk")) {
      std::cerr << "Could not select quick_hk\n";
      return RimeSessionId{0};
    }
    sessions.push_back(session);
    return session;
  };
  auto session = add_session();
  if (!session) return 1;
  std::string line;
  while (true) {
    if (argc == 5) {
      while (g_main_context_iteration(nullptr, false)) {}
      pollfd input_fd = {STDIN_FILENO, POLLIN, 0};
      if (poll(&input_fd, 1, 10) == 0) continue;
    }
    if (!std::getline(std::cin, line)) break;
    std::istringstream input(line);
    std::string command;
    input >> command;
    bool handled = true;
    auto before = std::chrono::steady_clock::now();
    if (command == "key") {
      int code = 0, modifiers = 0;
      input >> code >> modifiers;
      handled = api->process_key(session, code, modifiers);
    } else if (command == "select") {
      int index = 0; input >> index;
      handled = index >= 0 && api->select_candidate(session, index);
    } else if (command == "clear") api->clear_composition(session);
    else if (command == "new") { session = add_session(); handled = session != 0; }
    else if (command == "use") {
      size_t index = 0; input >> index;
      if (index >= sessions.size()) handled = false;
      else session = sessions[index];
    } else if (command == "option") {
      std::string name; int value; input >> name >> value;
      api->set_option(session, name.c_str(), value != 0);
    } else if (command == "sync") handled = api->sync_user_data();
    else if (command == "quit") break;
    else if (command != "snapshot") handled = false;
    double elapsed = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - before).count();
    snapshot(api, session, handled, elapsed);
  }
  for (auto id : sessions) api->destroy_session(id);
  api->finalize();
}

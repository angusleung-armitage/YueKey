#include <rime_api.h>
#include <filesystem>
#include <iostream>
#include <string>

int main(int argc, char** argv) {
  if (argc != 5 || std::string(argv[1]) != "--build") {
    std::cerr << "Usage: quick-hk-deployer --build USER_DIR SHARED_DIR BUILD_DIR\n";
    return 2;
  }
  std::filesystem::create_directories(argv[4]);
  auto* api = rime_get_api();
  RIME_STRUCT(RimeTraits, traits);
  traits.user_data_dir = argv[2];
  traits.shared_data_dir = argv[3];
  traits.prebuilt_data_dir = argv[4];
  traits.staging_dir = argv[4];
  traits.app_name = "quick_hk.deployer";
  traits.log_dir = argv[4];
  api->setup(&traits);
  api->deployer_initialize(&traits);
  const auto schema = std::filesystem::path(argv[2]) / "quick_hk.schema.yaml";
  bool ok = api->deploy_schema(schema.c_str());
  ok = api->deploy_config_file("default.yaml", "config_version") && ok;
  if (std::filesystem::exists(std::filesystem::path(argv[2]) / "ibus_rime.yaml") ||
      std::filesystem::exists(std::filesystem::path(argv[3]) / "ibus_rime.yaml"))
    ok = api->deploy_config_file("ibus_rime.yaml", "config_version") && ok;
  api->finalize();
  return ok ? 0 : 1;
}

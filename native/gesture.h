// SPDX-License-Identifier: MIT
#pragma once
#include <cstdint>

namespace quick_hk {
// Times are monotonic milliseconds. Modifier-only taps never consume presses.
class DoubleControl {
 public:
  explicit DoubleControl(int key = 0xffe3) : key_(key) {}
  void Reset() { down_ = false; first_ = -1; }
  bool Feed(int key, bool release, bool other_modifiers, int64_t now) {
    if (key != key_ || other_modifiers) { Reset(); return false; }
    if (!release) {
      if (down_) { Reset(); return false; }  // auto-repeat invalidates a hold
      down_ = true;
      pressed_ = now;
      return false;
    }
    if (!down_) { Reset(); return false; }
    down_ = false;
    if (now - pressed_ > 250) { Reset(); return false; }
    if (first_ >= 0 && now - first_ <= 400) { Reset(); return true; }
    first_ = now;
    return false;
  }
 private:
  int key_;
  bool down_ = false;
  int64_t first_ = -1, pressed_ = 0;
};
}  // namespace quick_hk

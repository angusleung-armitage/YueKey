#include "gesture.h"
#include <cstdlib>
#include <iostream>

void check(bool value) { if (!value) std::abort(); }
int main() {
  quick_hk::DoubleControl g;
  check(!g.Feed(0xffe3, false, false, 0));
  check(!g.Feed(0xffe3, true, false, 50));
  check(!g.Feed(0xffe3, false, false, 100));
  check(g.Feed(0xffe3, true, false, 150));
  for (int invalid : {0, 1, 2, 3}) {
    g.Reset(); g.Feed(0xffe3, false, false, 1000);
    if (invalid == 0) g.Feed('c', false, true, 1010);
    if (invalid == 1) g.Feed(0xffe3, false, false, 1010);
    g.Feed(0xffe3, true, false, invalid == 2 ? 1300 : 1050);
    const int next = invalid == 3 ? 1600 : 1350;
    g.Feed(0xffe3, false, false, next);
    check(!g.Feed(0xffe3, true, false, next + 10));
  }
  g.Reset(); check(!g.Feed(0xffe3, true, false, 0));
  quick_hk::DoubleControl right(0xffe4);
  right.Feed(0xffe4, false, false, 0); right.Feed(0xffe4, true, false, 10);
  right.Feed(0xffe4, false, false, 20); check(right.Feed(0xffe4, true, false, 30));
  std::cout << "PASS double Ctrl, chords, repeats, holds, timeout, unmatched release, right Ctrl\n";
}

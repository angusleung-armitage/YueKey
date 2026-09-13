# Source attribution and licensing

Original YueKey code is MIT-licensed; see LICENSE. This applies to original
code, documentation and artwork only. Generated dictionaries are not MIT.
GPL-3.0, LGPL-3.0 and CC-BY-4.0 texts are included in LICENSES/.
On Debian/Ubuntu, the GPL-3 and LGPL-3 texts are also available in
`/usr/share/common-licenses/GPL-3` and `/usr/share/common-licenses/LGPL-3`.
Data and vendored code retain their respective licenses; this file does not
relicense third-party material. Dictionary sources and their licenses are listed below.

| Input | Source | License / notice |
|---|---|---|
| Cangjie 5 base table | https://github.com/rime/rime-cangjie | Repository LGPL-3.0; base table carries its own GPL notice and credits 五倉世紀 / chinesecj.com. Preserve both notices. |
| Quick supplementary table | https://github.com/rime/rime-quick | LGPL-3.0, upstream LICENSE retained. |
| Cantonese vocabulary and frequencies | https://github.com/rime/rime-cantonese | CanCLID, CC-BY-4.0. Uses essay-cantonese.txt, jyut6ping3.words.dict.yaml, jyut6ping3.phrase.dict.yaml. The separately ODbL-licensed maps dataset is not used. |
| Hong Kong supplementary mappings | https://gitlab.freedesktop.org/cangjie/libcangjie | Upstream data/table.txt declared public domain; imported from the checksum-pinned Ubuntu libcangjie3-data package. Full package copyright included. |
| Prediction plugin | https://github.com/rime/librime-predict | BSD-3-Clause. Pinned revision in vendor/librime-predict/UPSTREAM, full license retained beside source. |
| Rime | https://github.com/rime/librime | BSD-3-Clause, installed separately by Ubuntu or Weasel. |
| Lua extension | https://github.com/hchunhui/librime-lua | BSD-3-Clause, installed separately by Ubuntu or Weasel. |
| SenseVoice Small Yue | https://huggingface.co/ASLP-lab/WSYue-ASR | Apache-2.0 model card; ASLP-lab Cantonese fine-tune of SenseVoice Small. |
| SenseVoice ONNX export | https://huggingface.co/csukuangfj/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2025-09-09 | Export by sherpa-onnx maintainers; revision and SHA-256 pinned in speech setup. |
| sherpa-onnx runtime | https://github.com/k2-fsa/sherpa-onnx | Apache-2.0; pinned CPU wheels retain upstream notices. |
| Silero VAD | https://github.com/snakers4/silero-vad | MIT; sherpa-compatible ONNX model downloaded separately with a pinned SHA-256. |
| CT-Transformer punctuation | https://modelscope.cn/models/iic/punc_ct-transformer_zh-cn-common-vocab272727-pytorch | Upstream model terms apply; sherpa-onnx INT8 export is downloaded separately and checksum verified. |
| OpenCC Python implementation | https://github.com/yichen0831/opencc-python | Apache-2.0; installed from a pinned wheel with its conversion dictionaries. |
| NumPy | https://numpy.org | BSD-3-Clause; installed from a pinned wheel with bundled dependency notices. |

YueKey transforms full Cangjie codes to their first and last letters, adds HK
code alternatives, assigns Cantonese frequency weights, and builds continuation
predictions by splitting observed words into prefix/suffix pairs. These are
modified datasets with project-specific candidate ordering.
Legacy `zx` punctuation codes come from the same public-domain libcangjie data,
reduce to first/last letters (`zxab` → `zb`), and retain full-code order as their
initial candidate ranking. The other upstream `z` symbol-category conventions
are excluded. These symbols do not expand the prediction corpus.
`data/sources.lock.json` records exact revisions, package versions, URLs, and
SHA-256 hashes. `tools/fetch_sources.py` verifies all inputs before use.

The prediction plugin has project-specific module/component names and per-engine
mutable prediction state. The immutable mapping database remains shared. Original
notices and the modified source accompany its binary package.

GNOME and Fcitx5 integrations use their installed native candidate renderers.
Original theme SVGs and CSS are part of YueKey. Fonts are supplied by Ubuntu's
fonts-noto-cjk package and are not bundled or modified here.

YueKey is an independent open-source project.

Windows distribution additions:

| Input | Source | License / notice |
|---|---|---|
| Weasel frontend | https://github.com/rime/weasel | GPL-3.0; installed separately from its official release, not bundled in YueKey. |
| sounddevice | https://github.com/spatialaudio/python-sounddevice | MIT; includes PortAudio binaries and their notices. |
| PortAudio | https://github.com/PortAudio/portaudio | MIT-style license; retain notices from the wheel. |
| comtypes | https://github.com/enthought/comtypes | MIT; Windows UI Automation bindings. |
| Python, Tcl/Tk | https://www.python.org/ and https://www.tcl-lang.org/ | PSF and Tcl/Tk licenses; included with the portable executable. |
| PyInstaller bootloader | https://github.com/pyinstaller/pyinstaller | GPL-2.0-or-later with bootloader exception permitting distribution of bundled applications under their own terms. |
| PyYAML | https://github.com/yaml/pyyaml | MIT. |
| CFFI | https://cffi.readthedocs.io/ | MIT. |

Windows ZIPs include wheel license/notice files in `LICENSES/runtime`, in addition
to the dependency lock. Speech weights are downloaded separately and are not
embedded in release packages. The corresponding source archive includes all
checksum-pinned dictionary inputs under `build/sources/` and the transformation
scripts, alongside the full GPL, LGPL and CC-BY texts. The generated character
dictionary retains the upstream GPL table notice; its supplemental mappings and
frequency inputs retain the LGPL/CC-BY terms above. These datasets are distributed
separately from the MIT tool code and are not relicensed by the root LICENSE.

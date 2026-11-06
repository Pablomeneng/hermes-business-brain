# Third-Party Notices

This plugin vendors and wraps **Obsidian-Bussines-Brain by unsulabs**
(https://github.com/unsulabs/Obsidian-Bussines-Brain), an MIT-licensed Python
toolkit for offline Obsidian "business brain" vaults.

## Vendored engine (verbatim, unmodified)

The directory `engine/scripts/` contains 38 upstream Python scripts copied
verbatim from the upstream repository, and `engine/` symlinks the bundled
`data/` directory (model schemas, baseline resources, vault templates) so the
scripts resolve their data with their original relative-path logic. Upstream
runtime log/JSON strings are intentionally left in the original language; no
script logic or identifiers were adapted. The wrapper code in this plugin
(`__init__.py`, `schemas.py`, `tools.py`, `engine/run_script.py`,
`engine/scripts/plugin_references.py`) is new, English, and MIT-licensed.

### Upstream license (verbatim)

MIT License

Copyright (c) 2026 Obsidian-Bussines-Brain contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Upstream's own third-party notices

The upstream repository's `THIRD_PARTY_NOTICES.md` (reproduced, abbreviated to
the notices relevant to the vendored materials):

### README organization

`README.md` and `README.es.md` in the upstream repository adapt the section
organization and navigation pattern of
[othneildrew/Best-README-Template](https://github.com/othneildrew/Best-README-Template/tree/fc444eb7b04b2e4863f6080b1507a219e95103fa),
revision `fc444eb7b04b2e4863f6080b1507a219e95103fa` (reviewed on `main`). Its
[LICENSE.txt at that revision](https://github.com/othneildrew/Best-README-Template/blob/fc444eb7b04b2e4863f6080b1507a219e95103fa/LICENSE.txt)
is **The Unlicense**, a public-domain dedication with an "AS IS" warranty
disclaimer. No upstream executable, logo, or screenshot is included in this
plugin. This attribution does not change the product's MIT license.

### ai-cursor-init documentation workflow

The documentation commands, configuration and templates in `.cursor/` and
`.cursor-init.yaml` of the upstream repository adapt the workflow of
[mgiovani/ai-cursor-init](https://github.com/mgiovani/ai-cursor-init/tree/fc15400e4baab4607f408f5b83fed19263e564e3),
revision `fc15400e4baab4607f408f5b83fed19263e564e3`. No upstream executable is
installed by this plugin. This notice applies to the derived material; it does
not relicense other project resources.

### ai-cursor-init upstream license (verbatim)

MIT License

Copyright (c) 2024 cursor-init contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Third-party Python dependencies (declared)

- **PyYAML==6.0.3** — MIT license (https://pyyaml.org/).
- **jsonschema>=4.23,<5** — MIT license (https://python-jsonschema.readthedocs.io/).

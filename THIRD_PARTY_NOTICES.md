# Third-party notices

DailyGrind bundles a derived CET-6 vocabulary dataset. The application code
does not include the original source repositories, only a transformed JSON
deck used for offline study.

## CET-6 frequency data and curated core list

- Repository: [wangjiuyi543-ui/cet6-vocabulary](https://github.com/wangjiuyi543-ui/cet6-vocabulary)
- License: MIT
- Used for: 2020–2025 CET-6 real-exam frequency ranking and the curated
  high-frequency core word order/meanings.
- The project attributes its source exam text to
  [AndrewYuZhenYu/cet6_exam_questions_txt_collection](https://github.com/AndrewYuZhenYu/cet6_exam_questions_txt_collection).
- Transformations for DailyGrind: removed empty/placeholder curated rows,
  intersected with a CET-6 wordbook, removed duplicate words, cleaned
  whitespace, and merged selected fields into JSON.

```text
MIT License

Copyright (c) 2026 wangjiuyi543-ui

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
```

## CET-4/CET-6 dictionary content

- Repository: [KyleBing/english-vocabulary](https://github.com/KyleBing/english-vocabulary)
- License: BSD 3-Clause
- Used for: Chinese definitions, phonetics and example sentences.
- Transformations for DailyGrind: selected CET-4/CET-6 entries, deduplicated
  words, selected concise definitions and examples, removed unused phrases and
  metadata, and normalized the result into JSON.

```text
BSD 3-Clause License

Copyright (c) 2022-2026, KyleBing

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its
   contributors may be used to endorse or promote products derived from
   this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```

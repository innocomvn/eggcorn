# Đóng góp cho eggcorn / Contributing

*(English below)*

## Kho "Nghễnh Ngãng" — từ tiếng Việt hay nghe nhầm

`data/vi/nghenh-ngang.csv` là kho mở các cặp **nghe thành → đúng ra là**: lỗi do người nghe hoặc máy
nhận dạng giọng nói (ASR) nghe nhầm, lỗi chính tả do phát âm vùng miền, từ tiếng Anh bị Việt hoá khi nói.
Kho dùng để dạy và chấm máy nghe tiếng Việt, và để ai viết biên bản, phụ đề cũng tra được.

Mỗi dòng là một cặp:

| cột | ý nghĩa | ví dụ |
|---|---|---|
| `heard` | cái nghe / máy viết ra | `i meo` |
| `meant` | cái người nói thật sự muốn nói | `email` |
| `kind` | `loanword` (từ mượn bị Việt hoá) · `asr` (máy nghe ra một từ Việt khác có nghĩa) · `spelling` (lỗi do phát âm) · `phrase` (cụm từ, thành ngữ) · `meaning` (nhầm nghĩa) | `loanword` |
| `cause` | lý do: `s/x`, `tr/ch`, `l/n`, `r/d/gi`, `hỏi/ngã`, `n/ng`, `c/t`, `v/d`, `loanword`, `sound-alike`, `meaning` | `loanword` |
| `region` | vùng hay gặp: `bac`, `trung`, `nam`, hoặc để trống | |
| `example` | một câu ví dụ **tự bạn viết** chứa từ đúng | `gửi email xác nhận` |
| `source` | `community` (bạn đóng góp), `general` (kiến thức chung), `asr-<nguồn>:<số lần>` | `community` |
| `verified` | `yes` nếu đã có người nghe lại xác nhận, `no` nếu chưa | `no` |

### Cách đóng góp

- **Không rành GitHub:** mở [Issue → "Thêm từ nghe nhầm"](../../issues/new?template=nghenh-ngang.yml), điền form.
  Người duy trì sẽ thêm giúp.
- **Rành GitHub:** sửa `data/vi/nghenh-ngang.csv` (thêm dòng ở cuối), chạy `eggcorn lexicon check`, mở Pull Request.

### Quy tắc (bắt buộc)

1. **Không thông tin cá nhân:** không tên người thật, số điện thoại, email, địa chỉ, biển số, mã khách hàng.
2. **Không bí mật công ty:** không tên dự án nội bộ, tên khách hàng, sản phẩm chưa công bố. Tên sản phẩm
   công khai (Zalo, Excel, Facebook…) thì được.
3. **Không chép nội dung có bản quyền:** câu ví dụ và giải thích phải do bạn tự viết. Có thể *tham khảo*
   các trang về từ dễ nhầm, nhưng không chép nguyên văn.
4. **Không ghi âm:** kho chỉ chứa chữ. Không gửi file âm thanh của người khác.
5. Một cặp chỉ một dòng; nếu đã có, hãy thêm vào `example` hoặc mở Issue để bàn.

Khi đóng góp, bạn đồng ý dữ liệu của mình được phát hành theo **CC BY 4.0** (`data/LICENSE`).
Mã nguồn theo Apache-2.0.

---

## English

`data/<lang>/*.csv` is an open lexicon of mishearings: what was heard (by a person or an ASR system)
and what was meant. Vietnamese is first (`data/vi`, "Nghễnh Ngãng" — Vietnamese for *hard of hearing*);
other languages are welcome in `data/<iso-code>/` with the same columns.

- English entries go to `data/en/eggcorns.csv` (`region`: empty, `us`, `uk`, `au` or `in`). Write your own
  example sentence; the classic eggcorns are common knowledge, but do not copy text from The Eggcorn Database.
- Open an issue with the "Add a mishearing" form, or edit the CSV and send a PR after
  `eggcorn lexicon check` passes (CI runs it too).
- No personal data, no confidential company terms, no copied text (write your own examples),
  no audio. Data contributions are licensed CC BY 4.0; code is Apache-2.0.

## Code

`python -m pytest` (or run `tests/test_core.py` directly) must pass. Keep the core free of third-party
dependencies.

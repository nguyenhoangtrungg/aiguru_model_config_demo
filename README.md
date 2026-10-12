# aiguru_model_config_demo

Quản lý cấu hình model bằng .env và config

Ứng dụng tóm tắt cùng văn bản bằng Ollama local hoặc OpenRouter cloud. Đổi provider, model, temperature, base URL bằng file môi trường. Bạn không cần sửa Python khi chuyển giữa hai adapter đã hỗ trợ.

## Cài đặt

Đã thử trên Ubuntu 20.04.6, Bash, Python 3.12.9. Repository: [nguyenhoangtrungg/aiguru_model_config_demo](https://github.com/nguyenhoangtrungg/aiguru_model_config_demo).

Với bản tài liệu hiện tại, dùng gói `aiguru_model_config_demo.zip` đi kèm để nhận đủ mã nguồn. Ngày 04/10/2026, remote vẫn ở bản khởi tạo chưa chứa ứng dụng. Sau khi bản code này được công bố, có thể lấy bằng:

```bash
git clone https://github.com/nguyenhoangtrungg/aiguru_model_config_demo.git
cd aiguru_model_config_demo
```

Nếu dùng ZIP, giải nén rồi mở thư mục `aiguru_model_config_demo`. Các lệnh bên dưới chạy ngay tại thư mục chứa `main.py`. Nếu chỉ thấy README và `.gitignore`, bạn đang dùng bản khởi tạo và cần quay lại gói ZIP. Dependency đã ghim yêu cầu Python từ 3.10, còn bản kiểm chứng dùng Python 3.12.9 được cài riêng. Kiểm tra `python3 --version` trước khi tạo venv:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
python -m pip check
```

Lock file bao gồm thư viện chạy ứng dụng và kiểm thử. `requirements.txt` liệt kê hai dependency trực tiếp. `requirements-test.txt` bổ sung pytest.

## Kiểm tra cấu hình (không gọi model)

```bash
cp .env.example .env.local
python main.py --env-file .env.local --check-config
```

Chỉ sao chép khi chưa có file cấu hình riêng. Tên `.env.local` hoặc `.env.cloud` không được chọn tự động, cần truyền qua `--env-file`. File local chọn `qwen2.5:7b`, temperature 0.2, URL `http://localhost:11434`, timeout 120 giây. Kiểm tra cục bộ chưa xác minh model/key/mạng.

## Chạy Ollama thật

Cài Ollama theo [hướng dẫn chính thức](https://docs.ollama.com/quickstart), khởi động dịch vụ và chuẩn bị model. Nếu dịch vụ chưa chạy, mở terminal khác, chạy `ollama serve` và giữ terminal đó mở. Quay lại terminal đã kích hoạt môi trường ảo:

```bash
ollama --version
ollama list
ollama pull qwen2.5:7b
python main.py --env-file .env.local
```

Bỏ qua bước pull nếu model đã có sẵn. `LLM_BASE_URL` chưa bao gồm `/api/chat`. Adapter này dành cho Ollama local không yêu cầu xác thực.

## Chạy OpenRouter thật

```bash
cp profiles/cloud.env.example .env.cloud
```

Mở `.env.cloud` bằng trình soạn thảo, điền `LLM_API_KEY` và thay `LLM_MODEL` bằng ID khả dụng. Lần xác minh dùng `google/gemma-4-26b-a4b-it`, temperature 0.7 và URL `https://openrouter.ai/api/v1`. Kiểm tra quyền truy cập, khả năng hỗ trợ temperature và chi phí của model trước khi gọi.

```bash
python main.py --env-file .env.cloud --check-config
python main.py --env-file .env.cloud
```

## Cấu hình và ưu tiên

`config.py` đọc đúng file được chọn bằng `dotenv_values(..., interpolate=False)`, rồi ghép biến tiến trình lên trên. Không tìm file ở thư mục cha và không sửa `os.environ`. Không truyền `--env-file` thì dùng `.env` cạnh `main.py`. File này có thể vắng nếu tiến trình đã nhận đủ biến. Đường dẫn tương đối truyền qua `--env-file` tính từ thư mục terminal đang đứng, còn dữ liệu `samples/source.txt` luôn nằm cạnh mã nguồn.

| Biến | Quy tắc |
| --- | --- |
| `LLM_PROVIDER` | `ollama` hoặc `openrouter` |
| `LLM_MODEL` | Bắt buộc, không rỗng/không còn tiền tố `replace-with-` |
| `LLM_BASE_URL` | HTTP(S), không user/password/query/fragment. OpenRouter dùng HTTPS |
| `LLM_TEMPERATURE` | Số hữu hạn trong 0–1, mặc định 0.2 |
| `LLM_TIMEOUT` | Số hữu hạn >0, mặc định 60 |
| `LLM_API_KEY` | Bắt buộc với OpenRouter. Không được ghi ra log |

Biến shell > file > mặc định. Biến rỗng không được hiểu là “không tồn tại”. Không dùng `${OTHER_VAR}` trong file. Project giữ giá trị nguyên văn.

```bash
LLM_TEMPERATURE=0.6 python main.py --env-file .env.local --check-config
unset LLM_PROVIDER LLM_MODEL LLM_TEMPERATURE
unset LLM_BASE_URL LLM_API_KEY LLM_TIMEOUT
python main.py --env-file profiles/missing-model.env.example
echo $?
```

Lệnh thiếu model phải kết thúc với mã 2 trước khi gọi model. Đọc mã thoát ngay sau lệnh Python. Mã 0 là hoàn tất hoặc check-config thành công, 1 là lỗi gọi model, 2 là lỗi cấu hình/dữ liệu/CLI. Timeout của Requests không phải tổng thời gian tối đa tuyệt đối của toàn tác vụ.

## Kiểm thử

```bash
python -m pytest -q
```

56 test offline đã qua, không skip. Request trong test adapter là giả lập. Hai lần live được ghi nhận riêng trong bộ tài liệu bài #48, không được suy ra từ số test.

## Đầu vào và đầu ra

Nguồn ở `samples/source.txt`. Câu chỉ dẫn tóm tắt nằm trong `main.py`. Kết quả in ra terminal, không tự tạo file đầu ra. Tóm tắt có thể sai nghĩa dù chương trình trả 0. Lần local diễn đạt “hơn 30 câu hỏi”, khác ý định đánh giá trên một bộ gồm 30 câu. Câu nguồn “đánh giá lại trên 30 câu hỏi” có thể gây hiểu nhầm, cần làm rõ đầu vào trước khi quy nguyên nhân cho model. Chương trình cũng chưa tự kiểm tra số ý trong bản tóm tắt.

Thêm provider khác cần adapter và validation tương ứng. Đổi URL chỉ phù hợp với endpoint hỗ trợ đúng giao thức. Không commit file môi trường riêng tư. Gói này không chứa key, không tự tạo tài khoản và không cấu hình dịch vụ Ollama.

Các file log và báo cáo kiểm chứng nằm trong thư mục `evidence/` của bộ tài liệu, bên ngoài repository ứng dụng và ZIP. Chúng không cần thiết để chạy ứng dụng.

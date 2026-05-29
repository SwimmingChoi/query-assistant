# vLLM SLM API 가이드 (사용자용)

> **대상**: API 사용자 (개발자, 챗봇/RAG 통합)
> **메인 모델**: `gemma-4-31B-it` (Google Gemma 4, 멀티모달)
> **Base URL**: `http://3.38.195.121:5015/v1` (외부)
> **API 호환**: OpenAI Chat Completions 100% — 기존 OpenAI SDK · LangChain `ChatOpenAI` · `curl` 그대로
> **인증**: 불필요 (`Authorization` 헤더 생략 가능)

자체 호스팅한 vLLM SLM(Small Language Model)을 **OpenAI API · Claude API 쓰듯** 호출하기 위한 가이드입니다.

처음 호출하는 분은 §1~§3만 보면 됩니다. 운영(서버 기동·튜닝·트러블슈팅·테스트)은 [`VLLM_OPS_GUIDE.md`](VLLM_OPS_GUIDE.md) 참고.

---

## 📑 목차

1. [한눈에 보기](#1-한눈에-보기)
2. [첫 호출](#2-첫-호출)
3. [핵심 기능](#3-핵심-기능)
   - 3.1 스트리밍 (SSE)
   - 3.2 Thinking 모드 (사고 과정 분리)
   - 3.3 이미지 멀티모달 (Vision)
   - 3.4 Tool Calling (함수 호출)
   - 3.5 멀티턴 대화
4. [파라미터·응답·에러 레퍼런스](#4-파라미터응답에러-레퍼런스)
5. [chatbot-poc 통합 (.env)](#5-chatbot-poc-통합-env)

---

## 1. 한눈에 보기

| 항목 | **Gemma (메인)** | Qwen3.6 (옵션) |
|------|------------------|----------------|
| Base URL | `http://3.38.195.121:5015/v1` | `http://3.38.195.121:5016/v1` |
| 모델명 (`model` 필드) | **`gemma-4-31B-it`** | `Qwen3.6-35B-A3B-FP8` |
| API 키 | 불필요 | 불필요 |
| 멀티모달 (이미지) | ✅ | ✅ |
| Tool Calling | ✅ | ✅ |
| 스트리밍 (SSE) | ✅ | ✅ |
| Thinking 기본값 | OFF (요청에서 활성화) | OFF (요청에서 활성화) |
| Thinking 활성화 옵션 | `enable_thinking: true` + `skip_special_tokens: false` | `enable_thinking: true` |
| Thinking 토큰 형식 | `<\|channel>...<channel\|>` (스페셜 토큰) | `<think>...</think>` (일반 토큰) |

> 컨텍스트 길이·동시 이미지 한도 등은 운영 튜닝값에 따라 달라집니다. 현재 값은 `GET /v1/models` 응답의 `max_model_len` 또는 운영자에게 확인.

**API 호환성**: vLLM은 OpenAI Chat Completions API와 **100% 호환**. `OpenAI` SDK · `langchain_openai.ChatOpenAI` · `fetch` · `curl` 어떤 클라이언트도 `base_url`만 바꾸면 그대로 동작합니다.

**엔드포인트 요약**:

| 메서드 | 경로 | 용도 |
|--------|------|------|
| POST | `/v1/chat/completions` | **메인 추론 API** (텍스트·이미지·툴 호출 모두) |
| GET | `/v1/models` | 로드된 모델 목록 |
| GET | `/health` | 서버 헬스체크 |

---

## 2. 첫 호출

> 호출 전 살아있는지 확인: `curl http://3.38.195.121:5015/health` → `200 OK`.

### 2.1 curl

```bash
curl http://3.38.195.121:5015/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemma-4-31B-it",
    "messages": [
      {"role": "system", "content": "간결하게 답변해."},
      {"role": "user",   "content": "대한민국의 수도는?"}
    ],
    "max_tokens": 100
  }'
```

응답:

```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "model": "gemma-4-31B-it",
  "choices": [{
    "index": 0,
    "message": {"role": "assistant", "content": "서울입니다."},
    "finish_reason": "stop"
  }],
  "usage": {"prompt_tokens": 25, "completion_tokens": 5, "total_tokens": 30}
}
```

### 2.2 Python (OpenAI SDK)

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://3.38.195.121:5015/v1",
    api_key="not-needed",   # vLLM 기본 인증 없음. 빈 문자열은 SDK가 거부하므로 더미값.
)

resp = client.chat.completions.create(
    model="gemma-4-31B-it",
    messages=[
        {"role": "system", "content": "간결하게 답변해."},
        {"role": "user",   "content": "파이썬이란?"},
    ],
    max_tokens=200,
    temperature=0.7,
)
print(resp.choices[0].message.content)
```

### 2.3 LangChain

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    base_url="http://3.38.195.121:5015/v1",
    model="gemma-4-31B-it",
    api_key="not-needed",
    temperature=0.7,
    max_tokens=200,
)

print(llm.invoke("대한민국의 수도는?").content)
```

### 2.4 Node.js (OpenAI SDK)

```javascript
import OpenAI from "openai";

const client = new OpenAI({
  baseURL: "http://3.38.195.121:5015/v1",
  apiKey: "not-needed",
});

const resp = await client.chat.completions.create({
  model: "gemma-4-31B-it",
  messages: [{ role: "user", content: "안녕" }],
  max_tokens: 100,
});

console.log(resp.choices[0].message.content);
```

### 2.5 모델 목록 확인

```bash
curl http://3.38.195.121:5015/v1/models
```

응답에 `served_model_name` (예: `gemma-4-31B-it`)과 `max_model_len`(현재 컨텍스트 한도)이 들어 있어, 클라이언트에서 모델명·컨텍스트 한도를 자동 감지하는 데 쓸 수 있습니다.

---

## 3. 핵심 기능

### 3.1 스트리밍 (SSE)

`stream: true`를 주면 토큰이 생성되는 즉시 Server-Sent Events로 흘러나옵니다.

**curl**:

```bash
curl http://3.38.195.121:5015/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemma-4-31B-it",
    "messages": [{"role": "user", "content": "긴 시 한 편 써줘"}],
    "max_tokens": 500,
    "stream": true,
    "stream_options": {"include_usage": true}
  }'
```

응답 (SSE):

```
data: {"choices":[{"delta":{"role":"assistant","content":""},"index":0}]}
data: {"choices":[{"delta":{"content":"봄"},"index":0}]}
data: {"choices":[{"delta":{"content":"날의"},"index":0}]}
...
data: {"choices":[],"usage":{"prompt_tokens":14,"completion_tokens":120,"total_tokens":134}}
data: [DONE]
```

- 각 청크는 `data: ` 접두사 + JSON
- `choices[].delta.content`에 새로 생성된 토큰 텍스트
- `data: [DONE]`이 스트림 종료 신호
- `stream_options.include_usage: true`를 넣으면 마지막 청크에 `usage`가 따라옴

**Python 스트리밍**:

```python
stream = client.chat.completions.create(
    model="gemma-4-31B-it",
    messages=[{"role": "user", "content": "긴 시 한 편"}],
    max_tokens=500,
    stream=True,
)
for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)
```

---

### 3.2 Thinking 모드 (사고 과정 분리)

모델이 답변 전에 **"생각"하는 과정**을 `reasoning` 필드로 **분리**해서 받을 수 있습니다. 추론·수학·복잡한 분석 등 사고 과정이 가치 있는 워크로드에 사용.

> 📌 **필드명 주의**: 현재 운영(vLLM 0.19.0+)은 `reasoning` 키를 사용합니다. OpenAI 공식 스펙은 `reasoning_content`이므로 vLLM 버전이 올라가면 키가 바뀔 수 있습니다. 안전한 클라이언트 코드는 `msg.get("reasoning") or msg.get("reasoning_content")` 패턴 권장.

**기본값**: 서버 기본 OFF (챗봇 응답 지연 최소화). 요청 단위로 ON/OFF.

**활성화 방법** (Gemma 4):

```json
{
  "chat_template_kwargs": {"enable_thinking": true},
  "skip_special_tokens": false
}
```

> ⚠️ **Gemma 4는 `skip_special_tokens: false` 필수**. Gemma 4의 thinking 토큰(`<|channel>...<channel|>`)은 스페셜 토큰이라 기본값으로는 제거되어 reasoning 분리가 안 됩니다.
> Qwen3.6은 `<think>...</think>`가 일반 토큰이라 이 옵션 불필요.

**curl 예시**:

```bash
curl http://3.38.195.121:5015/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemma-4-31B-it",
    "messages": [
      {"role": "user", "content": "한 자리 소수를 모두 나열해줘. 이유도 설명해."}
    ],
    "max_tokens": 1000,
    "chat_template_kwargs": {"enable_thinking": true},
    "skip_special_tokens": false
  }'
```

응답:

```json
{
  "choices": [{
    "message": {
      "role": "assistant",
      "content": "한 자리 소수는 2, 3, 5, 7입니다.",
      "reasoning": "1은 소수가 아니고... 4=2×2, 6=2×3, 8=2³, 9=3²이므로 합성수..."
    },
    "finish_reason": "stop"
  }]
}
```

**Python 예시** (OpenAI SDK는 vLLM 전용 옵션을 `extra_body`로 전달):

```python
resp = client.chat.completions.create(
    model="gemma-4-31B-it",
    messages=[{"role": "user", "content": "12를 소인수분해해줘"}],
    max_tokens=1500,
    extra_body={
        "chat_template_kwargs": {"enable_thinking": True},
        "skip_special_tokens": False,
    },
)
print("🤔 사고 과정:")
print(resp.choices[0].message.reasoning)
print("\n💬 최종 답변:")
print(resp.choices[0].message.content)
```

**주의 사항**:

- Thinking ON이면 응답 토큰이 보통 2~4배(2K~4K 추가)로 늘어납니다 → `max_tokens`를 1,000 이상으로 잡으세요.
- 멀티턴 히스토리에 **사고 과정은 다시 넣지 마세요** — `messages`엔 최종 `content`만 포함. Reasoning은 일회용입니다.
- Thinking OFF 응답에는 `reasoning` 필드가 `null`.

---

### 3.3 이미지 멀티모달 (Vision)

이미지 + 텍스트를 함께 보내 비전 추론을 받습니다. Gemma 4는 OCR·차트·문서 QA를 지원하는 vision 모델입니다.

**입력 형식 2가지**:

| 형식 | 사용 시 |
|------|--------|
| `image_url` | 공개 URL (외부 접근 가능 이미지) |
| `data URL (base64)` | 로컬 파일, 스크린샷 등 |

> 한 요청당 첨부 가능 이미지 수는 운영 튜닝값(`limit_mm_per_prompt.image`)에 따라 달라집니다. 초과 시 HTTP 422가 반환되니 작게 시작해 늘려보세요. 정확한 현재 한도는 운영자에게 확인.

**curl — URL 입력**:

```bash
curl http://3.38.195.121:5015/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemma-4-31B-it",
    "messages": [{
      "role": "user",
      "content": [
        {"type": "image_url", "image_url": {"url": "https://example.com/cat.jpg"}},
        {"type": "text",      "text": "이 이미지에 무엇이 보이나요?"}
      ]
    }],
    "max_tokens": 500
  }'
```

**curl — Base64 입력**:

```bash
# Linux (GNU coreutils)
B64=$(base64 -w0 ./screenshot.png)
# macOS (BSD base64 — `-w0` 미지원, 기본이 한 줄 출력)
# B64=$(base64 -i ./screenshot.png | tr -d '\n')

curl http://3.38.195.121:5015/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"gemma-4-31B-it\",
    \"messages\": [{
      \"role\": \"user\",
      \"content\": [
        {\"type\": \"image_url\", \"image_url\": {\"url\": \"data:image/png;base64,${B64}\"}},
        {\"type\": \"text\",      \"text\": \"이 화면의 텍스트를 모두 추출해줘.\"}
      ]
    }],
    \"max_tokens\": 1500
  }"
```

**Python — 로컬 파일을 base64로**:

```python
import base64
from openai import OpenAI

client = OpenAI(base_url="http://3.38.195.121:5015/v1", api_key="not-needed")

with open("./document.png", "rb") as f:
    b64 = base64.b64encode(f.read()).decode()

resp = client.chat.completions.create(
    model="gemma-4-31B-it",
    messages=[{
        "role": "user",
        "content": [
            {"type": "image_url",
             "image_url": {"url": f"data:image/png;base64,{b64}"}},
            {"type": "text",
             "text": "이 문서의 핵심 내용을 3줄로 요약해줘."},
        ],
    }],
    max_tokens=800,
)
print(resp.choices[0].message.content)
```

**Python — 이미지 + Thinking 동시**:

```python
resp = client.chat.completions.create(
    model="gemma-4-31B-it",
    messages=[{
        "role": "user",
        "content": [
            {"type": "image_url",
             "image_url": {"url": f"data:image/png;base64,{b64}"}},
            {"type": "text", "text": "이 차트가 보여주는 트렌드는?"},
        ],
    }],
    max_tokens=2000,
    extra_body={
        "chat_template_kwargs": {"enable_thinking": True},
        "skip_special_tokens": False,
    },
)
print("사고:", resp.choices[0].message.reasoning)
print("답변:", resp.choices[0].message.content)
```

**해상도/사용 팁**:

- 이미지가 너무 작으면 (예: 50×50 아이콘) 모델이 "잘 안 보인다"고 답할 수 있음 → 원본 해상도를 유지해서 보내세요.
- 동일 요청에 너무 많은 이미지를 묶으면 HTTP 422 (운영 한도 초과). 안전하게 한두 장씩 끊어 보내거나 운영자에게 한도 확인.
- 디테일이 중요한 문서/차트는 PNG 같은 무손실 포맷 권장 (JPEG는 글자 가장자리 흐림).

---

### 3.4 Tool Calling (함수 호출)

모델이 외부 함수를 **호출하기로 결정**하면 OpenAI 호환 JSON으로 자동 파싱되어 옵니다. `tools` 정의 → 모델이 `tool_calls` 응답 → 클라이언트가 실제 함수 실행 → 결과를 `role: "tool"` 메시지로 다시 전달 → 최종 답변.

**1단계 — Tool 정의 + 사용자 질문**:

```bash
curl http://3.38.195.121:5015/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemma-4-31B-it",
    "messages": [{"role": "user", "content": "서울 날씨 알려줘"}],
    "tools": [{
      "type": "function",
      "function": {
        "name": "get_weather",
        "description": "지정한 도시의 현재 날씨를 조회합니다.",
        "parameters": {
          "type": "object",
          "properties": {
            "city": {"type": "string", "description": "도시 이름"}
          },
          "required": ["city"]
        }
      }
    }],
    "max_tokens": 300
  }'
```

응답 — 모델이 함수 호출을 결정:

```json
{
  "choices": [{
    "message": {
      "role": "assistant",
      "content": null,
      "tool_calls": [{
        "id": "chatcmpl-tool-abc",
        "type": "function",
        "function": {
          "name": "get_weather",
          "arguments": "{\"city\": \"서울\"}"
        }
      }]
    },
    "finish_reason": "tool_calls"
  }]
}
```

**2단계 — 함수 실행 결과를 다시 전달**:

```bash
curl http://3.38.195.121:5015/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemma-4-31B-it",
    "messages": [
      {"role": "user", "content": "서울 날씨 알려줘"},
      {
        "role": "assistant",
        "content": null,
        "tool_calls": [{
          "id": "call_1",
          "type": "function",
          "function": {"name": "get_weather", "arguments": "{\"city\": \"서울\"}"}
        }]
      },
      {
        "role": "tool",
        "tool_call_id": "call_1",
        "content": "{\"temperature\": 22, \"condition\": \"맑음\", \"humidity\": 45}"
      }
    ],
    "max_tokens": 300
  }'
```

최종 응답:

```json
{
  "choices": [{
    "message": {
      "role": "assistant",
      "content": "현재 서울은 22°C, 맑음이며 습도는 45%입니다."
    },
    "finish_reason": "stop"
  }]
}
```

**LangChain `bind_tools`**:

```python
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool

@tool
def get_weather(city: str) -> str:
    """지정한 도시의 현재 날씨를 조회합니다."""
    return f"{city}: 22°C, 맑음"

llm = ChatOpenAI(
    base_url="http://3.38.195.121:5015/v1",
    model="gemma-4-31B-it",
    api_key="not-needed",
)
llm_with_tools = llm.bind_tools([get_weather])
resp = llm_with_tools.invoke("서울 날씨 알려줘")
print(resp.tool_calls)
# → [{'name': 'get_weather', 'args': {'city': '서울'}, 'id': 'chatcmpl-tool-...'}]
```

> Tool이 필요 없다고 모델이 판단하면 `tool_calls` 없이 `content`로 바로 답변합니다.

---

### 3.5 멀티턴 대화

이전 응답을 그대로 `messages`에 누적해 보내면 됩니다. 별도 세션 ID 관리 불필요 (stateless).

```python
messages = [
    {"role": "system", "content": "간결한 한국어 비서."},
    {"role": "user",   "content": "내 이름은 홍길동이야."},
]

resp1 = client.chat.completions.create(
    model="gemma-4-31B-it", messages=messages, max_tokens=100,
)
messages.append({"role": "assistant", "content": resp1.choices[0].message.content})

messages.append({"role": "user", "content": "내 이름이 뭐였지?"})
resp2 = client.chat.completions.create(
    model="gemma-4-31B-it", messages=messages, max_tokens=100,
)
print(resp2.choices[0].message.content)   # → "홍길동님이라고 하셨습니다."
```

**역할 (`role`) 규칙**:

| role | 설명 |
|------|------|
| `system` | 모델의 역할·톤 지시 (선택, 1개 권장, 맨 앞) |
| `user` | 사용자 입력 |
| `assistant` | 모델의 이전 응답 (멀티턴 누적) |
| `tool` | Tool 실행 결과 (Tool Calling 시) |

**프리픽스 캐싱**: 동일 `system` 프롬프트로 반복 호출하면 vLLM이 KV 캐시를 재사용해 TTFT(첫 토큰 대기시간)를 크게 줄여줍니다 — 챗봇 시나리오에 자동 적용. 별도 옵션 불필요.

---

## 4. 파라미터·응답·에러 레퍼런스

### 4.1 자주 쓰는 요청 파라미터

| 파라미터 | 필수 | 기본값 | 설명 |
|----------|:----:|--------|------|
| `model` | O | — | `gemma-4-31B-it` 또는 `Qwen3.6-35B-A3B-FP8` |
| `messages` | O | — | 대화 메시지 배열 |
| `max_tokens` | — | 모델 한계 | 최대 생성 토큰 수. Thinking ON이면 1,000+ 권장 |
| `temperature` | — | 모델별 | 0=결정적, 1.0=기본. Gemma 4 권장 1.0, Qwen3.6 코딩 0.6 |
| `top_p` | — | 0.95 | Nucleus sampling |
| `top_k` | — | 모델별 | Gemma 4: 64, Qwen3.6: 20 |
| `seed` | — | — | 재현 가능한 출력 (`temperature=0`과 함께) |
| `stop` | — | — | 생성 중단 토큰(들) |
| `stream` | — | false | true면 SSE 스트리밍 |
| `stream_options` | — | — | `{"include_usage": true}`면 스트리밍 마지막 청크에 usage 포함 |
| `tools` | — | — | Tool Calling 함수 정의 |
| `chat_template_kwargs` | — | — | 템플릿 인자. `{"enable_thinking": true}` 등 |
| `skip_special_tokens` | — | true | **Gemma 4 Thinking 시 false 필수** |
| `presence_penalty` | — | 0 | Qwen3.6 Thinking에선 1.0~1.5 권장 (반복 붕괴 방지) |
| `extra_body` (Python SDK) | — | — | OpenAI 표준 외 vLLM 옵션 wrapping용 |

### 4.2 응답 형식

```json
{
  "id": "chatcmpl-xxx",
  "object": "chat.completion",
  "created": 1738200000,
  "model": "gemma-4-31B-it",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "...",                  // 텍스트 답변
      "reasoning": "...",                // (Thinking ON 시) 사고 과정 — vLLM 0.19.0 기준
      "tool_calls": [...]                // (함수 호출 시)
    },
    "finish_reason": "stop"
  }],
  "usage": {"prompt_tokens": 25, "completion_tokens": 120, "total_tokens": 145}
}
```

`finish_reason`:

| 값 | 의미 |
|----|------|
| `stop` | 자연 종료 (EOS 토큰 생성) |
| `length` | `max_tokens` 도달로 잘림 — `max_tokens`를 늘리세요 |
| `tool_calls` | Tool 호출 요청 |

### 4.3 에러 코드

| HTTP | 의미 | 흔한 원인 |
|------|------|----------|
| **400** | Bad Request | 파라미터 값 범위 위반 (예: `temperature: -1`) |
| **404** | Not Found | 잘못된 모델명 또는 엔드포인트 경로 |
| **422** | Unprocessable | 요청 바디 파싱 실패, 멀티모달 한도 초과 (이미지 3장 등) |
| **500** | Internal Error | 서버 측 문제 — 잠시 후 재시도, 지속 시 운영자 문의 |

응답 형식:

```json
{
  "object": "error",
  "message": "temperature must be non-negative, got -1.0.",
  "type": "BadRequestError",
  "code": 400
}
```

### 4.4 모델별 권장 샘플링

| 모델 | 모드 | temperature | top_p | top_k | presence_penalty | 출처 |
|------|------|:-----------:|:-----:|:-----:|:----------------:|------|
| gemma-4-31B-it | 일반 | 1.0 | 0.95 | 64 | 0 | 모델 `generation_config.json` 기본값 |
| Qwen3.6-35B-A3B | Thinking·일반 | 1.0 | 0.95 | 20 | **1.5** | Qwen3.6 모델 카드 |
| Qwen3.6-35B-A3B | Thinking·코딩 | 0.6 | 0.95 | 20 | 0 | Qwen3.6 모델 카드 |
| Qwen3.6-35B-A3B | Instruct·일반 | 0.7 | 0.8 | 20 | **1.5** | Qwen3.6 모델 카드 |

> 모델 `generation_config.json`이 자동 적용되므로 보통 명시 생략 가능. 한국어 응답에서 언어 혼합이 보이면 `presence_penalty` 1.0~1.2 권장. 결정적 출력이 필요하면 `temperature: 0` + `seed` 명시.

---

## 5. chatbot-poc 통합 (.env)

LangChain `ChatOpenAI` 기반 chatbot-poc는 `.env`만 바꾸면 즉시 vLLM SLM으로 전환됩니다.

```env
PROVIDER=huggingface
HF_BASE_URL=http://3.38.195.121:5015/v1   # Gemma 게이트웨이
# HF_BASE_URL=http://3.38.195.121:5016/v1 # Qwen 게이트웨이
CHAT_MODEL=gemma-4-31B-it             # 또는 Qwen3.6-35B-A3B-FP8
RERANKER_MODEL=gemma-4-31B-it
```

> ⚠️ **`PROVIDER`는 단일 스택** — Chat과 Embedding이 함께 전환됩니다. 임베딩은 OpenAI 유지하면서 Chat만 vLLM으로 쓰려면 provider 분리가 필요합니다.


---

## 다음 단계

- 서버 운영(기동/중지·모델 교체·튜닝·트러블슈팅): [`VLLM_OPS_GUIDE.md`](VLLM_OPS_GUIDE.md)
- 배포 절차(로컬 → S3 → EC2): [`DEPLOY_GUIDE.md`](DEPLOY_GUIDE.md)

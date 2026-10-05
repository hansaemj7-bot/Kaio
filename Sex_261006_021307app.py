import streamlit as st
import json
import os
from google import genai
from google.genai import types

모델 설정: Gemini 3.8 Flash
MODEL_NAME = "gemini-3.8-flash"

디렉토리 설정
DATA_DIR = "story_data"
CHARACTERS_FILE = os.path.join(DATA_DIR, "characters.json")
WORLDS_FILE = os.path.join(DATA_DIR, "worlds.json")
CHATS_DIR = os.path.join(DATA_DIR, "chats")
STATES_DIR = os.path.join(DATA_DIR, "states")

for path in [DATA_DIR, CHATS_DIR, STATES_DIR]:
os.makedirs(path, exist_ok=True)

def load_json(filepath, default):
if os.path.exists(filepath):
try:
with open(filepath, "r", encoding="utf-8") as f:
return json.load(f)
except Exception:
return default
return default

def save_json(filepath, data):
with open(filepath, "w", encoding="utf-8") as f:
json.dump(data, f, ensure_ascii=False, indent=2)

기본 세계관 및 캐릭터 데이터
default_worlds = {
"루미나스 아카데미": "마법과 공학이 결합된 학원. 결계 균열 사고가 자주 일어나는 판타지 세계관.",
"네오 바빌론 2180": "거대 기업 연합이 통제하는 네온사인 가득한 디스토피아 사이버펑크 도시."
}
default_chars = {
"엘레나 (수석 연금술사)": {
"world": "루미나스 아카데미",
"description": "차가운 원칙주의자이나 호기심이 생기면 위험한 실험도 서슴지 않는다. 존댓말과 학구적인 어조를 쓴다.",
"first_message": "기다리고 있었습니다. 결계 파편 분석 작업 준비는 끝마치셨습니까?"
},
"하이드 (정보 브로커)": {
"world": "네오 바빌론 2180",
"description": "골목길 뒷골목 넷러너. 능글맞고 잇속에 밝으며 거친 반말을 쓴다. 돈과 유용한 정보를 좋아한다.",
"first_message": "어이, 발소리 좀 죽이지 그래? 기업 감시 드론이 방금 지나갔다고."
}
}

worlds = load_json(WORLDS_FILE, default_worlds)
characters = load_json(CHARACTERS_FILE, default_chars)

실시간 상태 추출 함수
def update_dynamic_state(client, char_name, world_name, current_state, user_msg, ai_reply):
prompt = f"""
당신은 캐릭터 롤플레잉 게임의 '상태 기록관'입니다.
오간 대화를 정밀 분석하여 변경되거나 새로 밝혀진 사실을 상태(JSON)로 갱신하세요.

[캐릭터 & 세계관]
캐릭터: {char_name} | 세계관: {world_name}

[현재 상태]
{json.dumps(current_state, ensure_ascii=False, indent=2)}

[최근 대화]
유저: {user_msg}
캐릭터: {ai_reply}

[지침]
1. 위치 변화, 유저와의 호감/관계 변화, 획득하거나 건넨 아이템/단서, 핵심 사건/약속을 반영하세요.
2. 반드시 아래 JSON 형식으로만 응답하세요:
{{
"current_location": "현재 위치",
"relationship_status": "유저와의 현재 관계/감정 상태",
"inventory_and_items": ["소지품 및 단서 목록"],
"key_memories": ["기억해야 할 핵심 사실 및 사건들"]
}}
"""
try:
res = client.models.generate_content(
model=MODEL_NAME,
contents=[prompt],
config=types.GenerateContentConfig(
response_mime_type="application/json",
temperature=0.2
)
)
return json.loads(res.text)
except Exception:
return current_state

UI 페이지 설정
st.set_page_config(page_title="AI 캐릭터 스토리 룸", page_icon="⚡", layout="wide")

사이드바
with st.sidebar:
st.header("⚙ 시스템 설정")
st.info(f"구동 모델: {MODEL_NAME}")

secret_key = st.secrets.get("GEMINI_API_KEY", "") if hasattr(st, "secrets") else ""
env_key = os.getenv("GEMINI_API_KEY", "")
default_key = secret_key or env_key

api_key = st.text_input("Gemini API Key", value=default_key, type="password", placeholder="AI Studio 키 입력")

st.markdown("---")
st.header("🌍 세계관 및 캐릭터")

with st.expander("➕ 새 세계관 등록"):
new_w_name = st.text_input("세계관 이름")
new_w_desc = st.text_area("세계관 설명")
if st.button("세계관 저장"):
if new_w_name and new_w_desc:
worlds[new_w_name] = new_w_desc
save_json(WORLDS_FILE, worlds)
st.success("세계관 등록 완료!")
st.rerun()

with st.expander("➕ 새 캐릭터 등록"):
new_c_name = st.text_input("캐릭터 이름")
new_c_world = st.selectbox("소속 세계관", options=list(worlds.keys()))
new_c_desc = st.text_area("성격, 말투, 특징")
new_c_intro = st.text_area("첫 대사")
if st.button("캐릭터 저장"):
if new_c_name and new_c_desc:
characters[new_c_name] = {
"world": new_c_world,
"description": new_c_desc,
"first_message": new_c_intro or "반갑습니다."
}
save_json(CHARACTERS_FILE, characters)
st.success("캐릭터 등록 완료!")
st.rerun()

st.markdown("---")
selected_char = st.selectbox("대화할 캐릭터", options=list(characters.keys()))

if not selected_char:
st.info("캐릭터를 선택해주세요.")
st.stop()

char_info = characters[selected_char]
world_name = char_info.get("world", "미지정")
world_desc = worlds.get(world_name, "설정 없음")

chat_file = os.path.join(CHATS_DIR, f"{selected_char}.json")
state_file = os.path.join(STATES_DIR, f"{selected_char}_state.json")

initial_state = {
"current_location": "시작 장소",
"relationship_status": "첫 만남",
"inventory_and_items": [],
"key_memories": ["이야기가 시작되었습니다."]
}

messages = load_json(chat_file, [
{"role": "assistant", "content": char_info.get("first_message", "반갑습니다.")}
])
live_state = load_json(state_file, initial_state)

레이아웃
col_chat, col_state = st.columns([7, 3])

with col_state:
st.subheader("🧠 실시간 저장 메모리")
st.caption("대화할 때마다 파일에 실시간 갱신됩니다.")
st.markdown(f"📍 위치:{live_state.get('current_location', '알 수 없음')}")
st.markdown(f"🤝 관계: {live_state.get('relationship_status', '미정')}")

st.markdown("🎒 소지품 / 단서:")
items = live_state.get("inventory_and_items", [])
if items:
for it in items:
st.markdown(f"- {it}")
else:
st.markdown("없음")

st.markdown("📌 누적된 사건 / 기억:")
mems = live_state.get("key_memories", [])
for m in mems:
st.markdown(f"- {m}")

st.markdown("---")
if st.button("🔄 대화 및 상태 완전 초기화"):
messages = [{"role": "assistant", "content": char_info.get("first_message", "반갑습니다.")}]
live_state = initial_state
save_json(chat_file, messages)
save_json(state_file, live_state)
st.rerun()

with col_chat:
st.title(f"📖 {selected_char}")
st.caption(f"세계관: {world_name} — {world_desc}")

for msg in messages:
with st.chat_message(msg["role"]):
st.markdown(msg["content"])

if prompt := st.chat_input("행동이나 대사를 입력하세요... (예: 문을 열고 들어오며 나 왔어.)"):
if not api_key:
st.error("사이드바에 Gemini API 키를 먼저 입력해주세요.")
st.stop()

messages.append({"role": "user", "content": prompt})
with st.chat_message("user"):
st.markdown(prompt)

client = genai.Client(api_key=api_key)

system_prompt = f"""
당신은 캐릭터 롤플레잉 게임 속 인물 '{selected_char}'입니다.
세계관과 [실시간 누적 상태]를 지키며 상대와 대화하고 서사를 진행하세요.

[세계관]
{world_desc}

[캐릭터 설정]
{char_info['description']}

[실시간 누적 상태 및 기억]
• 현재 위치: {live_state.get('current_location')}
• 현재 관계/태도: {live_state.get('relationship_status')}
• 소지품/단서: {', '.join(live_state.get('inventory_and_items', []))}
• 핵심 기억: {'; '.join(live_state.get('key_memories', []))}

[규칙]
1. 절대 AI임을 밝히지 말고, 캐릭터 1인칭으로만 대답하세요.
2. 지문(행동 및 묘사)과 대사를 적절히 조합하세요.
3. 누적된 기억과 호감도 변화를 대화에 반영하세요.
"""

contents = []
for m in messages:
role = "user" if m["role"] == "user" else "model"
contents.append(types.Content(
role=role,
parts=[types.Part.from_text(text=m["content"])]
))

with st.chat_message("assistant"):
with st.spinner("생각 중..."):
response = client.models.generate_content(
model=MODEL_NAME,
contents=contents,
config=types.GenerateContentConfig(
system_instruction=system_prompt,
temperature=0.85
)
)
reply = response.text
st.markdown(reply)

messages.append({"role": "assistant", "content": reply})
save_json(chat_file, messages)

# 상태 갱신
with st.spinner("상태 저장 중..."):
updated_state = update_dynamic_state(
client=client,
char_name=selected_char,
world_name=world_name,
current_state=live_state,
user_msg=prompt,
ai_reply=reply
)
save_json(state_file, updated_state)

st.rerun()
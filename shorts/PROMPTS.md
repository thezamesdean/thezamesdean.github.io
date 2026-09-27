# AI 이미지 프롬프트 (실사 · 캠코더 저화질)

ChatGPT(이미지 생성), Gemini, Midjourney 등에 그대로 붙여넣으세요. 영어로 쓰는 게 결과가 더 좋습니다.
세로 사진(9:16 또는 3:4)으로 뽑고, 받은 파일을 `examples/` 폴더에 적힌 파일명으로 저장하면 됩니다.

영상 쪽에서 캠코더 효과(뭉개진 화질·노이즈·REC·날짜)를 한 번 더 입히기 때문에, 이미지는 "평범한 가족 사진"
정도의 사실감만 나오면 충분합니다. 너무 선명하고 예쁜 결과가 나오면 "less polished, more amateur"를 추가하세요.

## 모든 프롬프트 공통 꼬리말 (맨 뒤에 붙이기)

```
candid amateur photo, shot on a cheap 2000s camcorder / old phone, slightly blurry, soft focus,
flat on-camera flash or dim indoor tungsten light, muted colors, visible noise, no makeup look,
real Korean home interior, natural skin texture with pores and blemishes, unposed, vertical 9:16,
not a studio photo, no text, no watermark
```

---

## 1. 다이어트 비포/애프터 — "야식 끊고 매일 줄넘기 1000개 3개월 한 아빠의 최후"

> **같은 사람으로 보이게 하는 법:** BEFORE를 먼저 뽑고, 그 이미지를 첨부한 상태에서 AFTER 프롬프트를 넣으세요.
> ("Use the attached photo. Same man, same face, same living room, same camera angle ...")

### `diet_before.jpg`
```
A heavyset Korean man in his mid-40s, about 100kg, sitting on a worn living room sofa late at night,
tight grey t-shirt stretched over his belly, a half-eaten fried chicken box and a beer can on the low table.
Facial expression: caught off guard by the camera, sheepish embarrassed half-smile, eyes squinting,
a little sweaty forehead, double chin, puffy cheeks, tired dark circles.
His hand is raised halfway as if saying "don't film me". TV glow on his face.
```

### `diet_after.jpg` (BEFORE 이미지 첨부 후)
```
Use the attached photo as reference. The SAME man, same face and same living room, same camera angle,
three months later and about 20kg lighter. Standing up, holding a jump rope, wearing the same grey t-shirt
which is now loose on him. Visibly slimmer face with a defined jawline, no double chin.
Facial expression: proud but shy grin, eyebrows slightly raised, cheeks flushed and sweaty
from exercise, trying not to laugh at the camera. Daylight from the window.
```

---

## 2. 랭킹 — "딸 남자친구 처음 본 아빠 표정 랭킹 TOP5"

> **팁:** 5장 모두 다른 아빠(다른 사람)라서 일관성 걱정은 없습니다. 표정이 핵심이라 얼굴이 화면 중앙 1/3 정도를 차지하게 하세요.

### `rank_dad5.jpg` — 5위 억지 미소 장인
```
A Korean father in his 50s standing at the front door of an apartment, greeting a young man (seen from behind, blurry).
Facial expression: forced polite smile, mouth smiling but eyes completely cold and not smiling,
tight jaw, one eyebrow slightly twitching. Wearing a cardigan over a polo shirt.
```

### `rank_dad4.jpg` — 4위 팔짱 스캔 모드
```
A stern Korean father in his 50s sitting on a sofa with arms crossed tightly, reading glasses low on his nose,
looking over the glasses at someone off-camera. Facial expression: suspicious scanning look, eyes narrowed,
lips pressed into a flat line, head slightly tilted back. Living room with a family photo on the wall.
```

### `rank_dad3.jpg` — 3위 과일 깎다 멈춤
```
A Korean father in his late 50s sitting at a dining table, peeling an apple with a small fruit knife,
completely frozen mid-motion, the apple peel hanging. Facial expression: frozen stare straight ahead,
eyes wide and unblinking, mouth slightly open, no emotion at all, eerie calm. Plate of cut fruit on the table.
```

### `rank_dad2.jpg` — 2위 현실 부정
```
A Korean father in his 50s in the living room, leaning forward with one hand cupped behind his ear,
Facial expression: exaggerated disbelief, eyebrows raised very high, forehead wrinkled, mouth open mid-word
as if saying "...who?", eyes blinking rapidly, head tilted. Comedic but realistic.
```

### `rank_dad1.jpg` — 1위 영혼 가출
```
A Korean father in his 60s slumped on a sofa, completely drained, staring into empty space.
Facial expression: soul has left the body, blank glassy eyes, mouth hanging open, face pale,
one tear rolling down his cheek, a TV remote slipping from his limp hand.
In the blurry foreground, the edge of a wedding invitation card on the table.
```

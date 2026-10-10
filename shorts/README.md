# 쇼츠 생성기 (비포/애프터 · 랭킹)

> **상태: 보류 (2026-10-10)**
> 다시 시작할 때: `PROMPTS.md`로 AI 실사 이미지 7장 만들기 → `examples/`에 파일명대로 저장 →
> `python3 make_short.py examples/diet_camcorder.json` / `examples/ranking_camcorder.json` 실행.
> 레퍼런스(2천만+ 조회수)와 반영한 패턴은 `REFERENCES.md` 참고.

JSON 하나 쓰고 명령어 한 줄이면 1080x1920 쇼츠 mp4가 나옵니다. 효과음(휙·팡·쿵)은 자동으로 들어갑니다.

```bash
pip install pillow numpy imageio-ffmpeg
python3 make_short.py examples/before_after.json   # -> out/before_after.mp4
python3 make_short.py examples/ranking.json        # -> out/ranking.mp4
```

사진 경로는 JSON 파일 기준 상대경로입니다. 사진이 없으면 샘플 이미지로 채워집니다.

## 비포/애프터 (`type: before_after`)
| 키 | 설명 |
|---|---|
| `hook` | 상단 후킹 문구 (줄 배열, 2번째 줄은 노란색) |
| `before` / `after` | `image`, `label`(알약 배지), `caption`(큰 글씨) |
| `bottom` | 마지막 좌우 비교 화면 문구 |
| `timing` | `before` / `transition` / `after` / `split` 초 (split 0이면 비교 화면 생략) |
| `music` | 배경음악 파일 (선택), `music_volume` 0~1 |

흐름: 비포(줌인) → 와이프 전환 + 플래시 → 애프터 → 좌우 비교

## 랭킹 (`type: ranking`)
| 키 | 설명 |
|---|---|
| `title` | 상단 제목 (줄 배열) |
| `items` | `rank`, `name`, `desc`, `image` |
| `per_item` | 항목당 초 (1위는 `first_bonus` 배, 기본 1.5) |
| `outro_text` | 마지막 문구 (예: 댓글 유도) |
| `music` | 배경음악 (선택) |

흐름: 빈 순위표 → 5위부터 "N위" 팝 + 이름 채워짐 → 1위는 쿵 효과음과 함께 길게 → 아웃트로

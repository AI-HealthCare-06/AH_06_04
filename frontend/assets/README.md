# frontend/assets — 홈페이지·발표용 영상

| 파일 | 내용 | 쓰는 곳 |
|---|---|---|
| `glowpass-intro.mp4` | **GlowPass 소개 영상 80초** · 1920×1080 · 30fps · 소리 있음(AAC) · H.264(yuv420p, faststart) · 7.8MB (원본 19MB 를 웹용으로 다시 인코딩) | 랜딩 페이지 메인 화면 자동 재생 |
| `glowpass-intro-poster.jpg` | 80초 영상 마지막 장면 (팀원 이름) — 영상이 뜨기 전·재생 안 될 때 | `<video poster>` |
| `glowpass-intro-33s.mp4` | 발표 오프닝용 짧은 모션그래픽 33초 · 무음 · 1MB | 데모데이 발표 첫 장 |
| `glowpass-intro-33s-poster.jpg` | 33초 영상 마지막 장면 | |

배포된 앱에서는 `/static/assets/glowpass-intro.mp4` 로 나온다 (`app/main.py` 가 `frontend/` 를 `/static` 에 올림).

## 홈페이지에 넣기 (자동 재생 · 무한 반복)

```html
<video class="hero-video" autoplay muted loop playsinline preload="metadata"
       poster="/static/assets/glowpass-intro-poster.jpg">
  <source src="/static/assets/glowpass-intro.mp4" type="video/mp4">
</video>
```

- `muted` 가 없으면 브라우저(크롬·사파리·모바일)가 자동 재생을 막는다. 소리는 들어 있으니 사용자가 켜고 싶으면 `controls` 를 붙이면 된다.
- `playsinline` 은 아이폰에서 전체 화면으로 튀지 않게.
- 다른 서버(별도 랜딩 페이지)에 올릴 땐 mp4 와 poster 두 파일을 복사하고 `src`·`poster` 경로만 바꾸면 된다.

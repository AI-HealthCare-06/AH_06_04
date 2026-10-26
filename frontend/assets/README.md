# frontend/assets — 홈페이지·발표용 영상

| 파일 | 내용 | 쓰는 곳 |
|---|---|---|
| `glowpass-intro.mp4` | GlowPass 소개 모션그래픽 33초 · 1920×1080 · 소리 없음 · H.264(yuv420p, faststart) | 랜딩 페이지 메인 화면 자동 재생, 발표 오프닝 |
| `glowpass-intro-poster.jpg` | 영상이 뜨기 전·재생 안 될 때 보여줄 정지 화면 (마지막 장면) | `<video poster>` |

배포된 앱에서는 `/static/assets/glowpass-intro.mp4` 로 나온다 (`app/main.py` 가 `frontend/` 를 `/static` 에 올림).

## 홈페이지에 넣기 (자동 재생 · 무한 반복)

```html
<video class="hero-video" autoplay muted loop playsinline preload="metadata"
       poster="/static/assets/glowpass-intro-poster.jpg">
  <source src="/static/assets/glowpass-intro.mp4" type="video/mp4">
</video>
```

- `muted` 가 없으면 브라우저(크롬·사파리·모바일)가 자동 재생을 막는다. 소리 없는 영상이라 문제 없음.
- `playsinline` 은 아이폰에서 전체 화면으로 튀지 않게.
- 다른 서버(별도 랜딩 페이지)에 올릴 땐 파일 두 개를 복사하고 `src`·`poster` 경로만 바꾸면 된다.
- 원본 소스는 HTML+CSS 애니메이션(`docs/` 가 아니라 발표 자료 쪽, 조태희 보관). 문구·숫자 수정이 필요하면 영상을 다시 뽑는다.

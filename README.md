# 경제 지표 대시보드

CNN 공포탐욕지수, 나스닥, S&P 500, 개별종목(엔비디아·테슬라·스페이스X·팔란티어)을 보는 GitHub Pages 사이트입니다.

## 동작 방식
브라우저에서 야후·CNN·네이버 등을 직접 호출하면 CORS 정책 때문에 거의 막히고 느립니다.
그래서 **GitHub Actions가 10분마다 서버에서 데이터를 가져와 `data/all.json` 파일 하나로 저장**하고,
사이트는 접속할 때 이 파일을 **딱 한 번** 읽습니다. 이후 카드·팝업 차트·요약 차트는 모두 메모리에서 바로 그려져 즉시 반응합니다.

- 시세/지수: Yahoo Finance (`scripts/fetch_data.py`)
- 공포탐욕지수: CNN
- 어떤 구간(예: 1년) 데이터가 빠져도 5년/최대 데이터로 대신 그려서 화면이 비지 않습니다.
- 인베스팅닷컴은 공식 API가 없고 자동 수집을 막아서 사용하지 않았습니다.

## 배포 순서
1. GitHub에서 **public** 저장소를 만듭니다 (예: `market-dashboard`).
2. 이 폴더의 파일을 모두 올립니다. 폴더 구조가 중요합니다:
   ```
   index.html
   symbols.json
   scripts/fetch_data.py
   .github/workflows/update.yml
   ```
   `.github` 폴더가 드래그 업로드로 안 올라가면 **Add file → Create new file**에서 파일 이름에
   `.github/workflows/update.yml`을 입력(슬래시가 폴더가 됩니다)하고 내용을 붙여 넣으세요.
3. **Settings → Pages** 에서 `Deploy from a branch` / `main` / `(root)` 선택 후 Save.
4. **Actions 탭 → update-data → Run workflow** 로 수동 실행합니다. 성공하면 `data/all.json`이 생기고 이후 10분마다 자동 갱신됩니다.
   (실패 시 Settings → Actions → General → Workflow permissions 를 `Read and write`로.)
5. `https://<아이디>.github.io/market-dashboard/` 접속.

이전 버전에서 만들어진 `data/NVDA.json` 같은 개별 파일은 더 이상 쓰지 않으니 삭제해도 됩니다.

## 종목 관리
- 기본 종목은 `symbols.json`에서 수정합니다 (`s`=야후 티커, `n`=표시 이름).
- 화면의 `+ 종목 추가`는 내 브라우저에서 바로 조회하는 임시 방식이라 무료 프록시에 의존해 느릴 수 있습니다.
  계속 볼 종목은 `symbols.json`에도 추가하면 빠르고 안정적입니다.

## 참고
- 스페이스X 티커는 `SPCX`(나스닥, 2026-06-12 상장)입니다.
- 데이터는 약 10분 간격이라 실시간 시세가 아닙니다. 화면은 접속 시 한 번만 조회하며, 최신으로 보려면 새로고침 버튼을 누르세요.
- 수집이 실패하면 이전 데이터를 유지합니다. Actions 탭 로그에서 어떤 구간이 비었는지 확인할 수 있습니다.

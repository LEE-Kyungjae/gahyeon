# 커스텀 음성 TTS

## Voicebox 연결

로컬 Voicebox의 녹음 9 프로필이 Discord 응답의 기본 TTS입니다.

```env
TTS_PROVIDER=voicebox
VOICEBOX_BASE_URL=http://127.0.0.1:17493
VOICEBOX_PROFILE_ID=1df376d5-c74d-415c-a2f0-fdb1654f7331
VOICEBOX_MODEL_SIZE=0.6B
VOICEBOX_TIMEOUT_SECONDS=300
```

봇은 Voicebox의 `/generate`에 생성을 요청하고 `/history/{id}`를 폴링한
후 `/audio/{id}`에서 WAV를 받습니다. Voicebox가 꺼져 있거나 생성에
실패하면 `TTS_FALLBACK_TO_EDGE=true`일 때 Edge TTS로 자동 전환합니다.

Voicebox 프로필과 모델은 현재 Mac의 로컬 Voicebox 저장소에 있습니다.
봇이 원격 서버나 컨테이너에서 실행되면 `127.0.0.1`은 그 원격 실행
환경을 가리키므로, 해당 서버에서 접근 가능한 HTTPS 엔드포인트나
SSH 터널 주소를 `VOICEBOX_BASE_URL`로 지정해야 합니다.

## 범용 HTTP 계약

가현봇은 음성 학습 엔진과 직접 결합하지 않고 HTTP 추론 서버를 통해 사용자 음성을 합성합니다.
GPT-SoVITS, Fish Speech, XTTS 등 실제 엔진은 이 계약을 구현하는 작은 어댑터 뒤에 배치합니다.

## 요청

`CUSTOM_TTS_ENDPOINT`로 `POST application/json` 요청을 보냅니다.

```json
{
  "text": "읽을 문장",
  "model": "my-korean-model",
  "speakerId": "my-voice",
  "format": "wav"
}
```

`CUSTOM_TTS_API_KEY`가 있으면 `Authorization: Bearer <key>` 헤더를 추가합니다.

## 응답

- 상태: `2xx`
- 본문: WAV 또는 MP3 원본 바이트
- Content-Type: `audio/wav` 또는 `audio/mpeg`

모델 파일은 봇 컨테이너가 아니라 추론 서버의 PVC/볼륨에 마운트합니다.
봇에는 모델 경로 대신 서버가 이해하는 `CUSTOM_TTS_MODEL` 별칭만 전달하는 것을 권장합니다.

## 활성화

```env
TTS_PROVIDER=custom
TTS_FALLBACK_TO_EDGE=true
CUSTOM_TTS_ENDPOINT=http://voice-server:8000/synthesize
CUSTOM_TTS_MODEL=my-korean-model
CUSTOM_TTS_SPEAKER_ID=my-voice
CUSTOM_TTS_FORMAT=wav
```

커스텀 서버가 준비되지 않았거나 요청이 실패하면 `TTS_FALLBACK_TO_EDGE=true`일 때 기존 Edge TTS를 사용합니다.

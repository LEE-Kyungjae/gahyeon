-- 날씨 데이터 테이블
CREATE TABLE weather_data (
    id BIGSERIAL PRIMARY KEY,
    temperature DOUBLE PRECISION NOT NULL,
    precipitation DOUBLE PRECISION NOT NULL,
    wind_speed DOUBLE PRECISION NOT NULL,
    precipitation_probability INTEGER,
    weather_description VARCHAR(50),
    fetched_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 최신 데이터 조회를 위한 인덱스
CREATE INDEX idx_weather_fetched_at ON weather_data(fetched_at DESC);

COMMENT ON TABLE weather_data IS '날씨 데이터 캐시 (Open-Meteo API)';
COMMENT ON COLUMN weather_data.temperature IS '현재 기온 (섭씨)';
COMMENT ON COLUMN weather_data.precipitation IS '강수량 (mm)';
COMMENT ON COLUMN weather_data.wind_speed IS '풍속 (km/h)';
COMMENT ON COLUMN weather_data.precipitation_probability IS '강수 확률 (%)';
COMMENT ON COLUMN weather_data.weather_description IS '날씨 설명 (맑음, 흐림 등)';

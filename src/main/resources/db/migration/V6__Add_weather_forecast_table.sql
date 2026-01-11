-- 날씨 예보 히스토리 테이블 (7일 예보, 히스토리 전체 보관)
CREATE TABLE weather_forecast (
    id BIGSERIAL PRIMARY KEY,
    city VARCHAR(50) NOT NULL,
    city_name VARCHAR(50) NOT NULL,
    country VARCHAR(50) NOT NULL,
    forecast_date DATE NOT NULL,
    temp_max DOUBLE PRECISION NOT NULL,
    temp_min DOUBLE PRECISION NOT NULL,
    precipitation_probability INTEGER,
    weather_description VARCHAR(50),
    fetched_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스 생성
CREATE INDEX idx_forecast_city_date ON weather_forecast(city, forecast_date);
CREATE INDEX idx_forecast_fetched ON weather_forecast(fetched_at DESC);
CREATE INDEX idx_forecast_city_date_fetched ON weather_forecast(city, forecast_date, fetched_at DESC);

COMMENT ON TABLE weather_forecast IS '날씨 예보 히스토리 (Open-Meteo API)';
COMMENT ON COLUMN weather_forecast.city IS '도시 코드 (City enum name)';
COMMENT ON COLUMN weather_forecast.city_name IS '도시 한글 이름';
COMMENT ON COLUMN weather_forecast.country IS '국가 이름';
COMMENT ON COLUMN weather_forecast.forecast_date IS '예보 대상 날짜';
COMMENT ON COLUMN weather_forecast.temp_max IS '최고 기온 (섭씨)';
COMMENT ON COLUMN weather_forecast.temp_min IS '최저 기온 (섭씨)';
COMMENT ON COLUMN weather_forecast.precipitation_probability IS '강수 확률 (%)';
COMMENT ON COLUMN weather_forecast.weather_description IS '날씨 설명 (맑음, 흐림 등)';
COMMENT ON COLUMN weather_forecast.fetched_at IS '데이터 조회 시점 (예보를 가져온 시간)';

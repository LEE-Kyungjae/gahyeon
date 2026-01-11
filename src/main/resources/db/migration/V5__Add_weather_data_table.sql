-- 날씨 데이터 테이블 (다중 도시 지원)
CREATE TABLE weather_data (
    id BIGSERIAL PRIMARY KEY,
    city VARCHAR(50) NOT NULL,
    city_name VARCHAR(50) NOT NULL,
    country VARCHAR(50) NOT NULL,
    temperature DOUBLE PRECISION NOT NULL,
    precipitation DOUBLE PRECISION NOT NULL,
    wind_speed DOUBLE PRECISION NOT NULL,
    precipitation_probability INTEGER,
    weather_description VARCHAR(50),
    fetched_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스 생성
CREATE INDEX idx_weather_city ON weather_data(city);
CREATE INDEX idx_weather_fetched_at ON weather_data(fetched_at DESC);
CREATE INDEX idx_weather_city_fetched ON weather_data(city, fetched_at DESC);

COMMENT ON TABLE weather_data IS '날씨 데이터 캐시 (Open-Meteo API)';
COMMENT ON COLUMN weather_data.city IS '도시 코드 (City enum name)';
COMMENT ON COLUMN weather_data.city_name IS '도시 한글 이름';
COMMENT ON COLUMN weather_data.country IS '국가 이름';
COMMENT ON COLUMN weather_data.temperature IS '현재 기온 (섭씨)';
COMMENT ON COLUMN weather_data.precipitation IS '강수량 (mm)';
COMMENT ON COLUMN weather_data.wind_speed IS '풍속 (km/h)';
COMMENT ON COLUMN weather_data.precipitation_probability IS '강수 확률 (%)';
COMMENT ON COLUMN weather_data.weather_description IS '날씨 설명 (맑음, 흐림 등)';

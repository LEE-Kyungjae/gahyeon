-- 운영에 이미 적용된 V5를 수정하지 않고, 멀티 도시 컬럼을 별도 마이그레이션으로 확장한다.
ALTER TABLE weather_data ADD COLUMN IF NOT EXISTS city VARCHAR(50);
ALTER TABLE weather_data ADD COLUMN IF NOT EXISTS city_name VARCHAR(50);
ALTER TABLE weather_data ADD COLUMN IF NOT EXISTS country VARCHAR(50);

-- 기존 단일 도시 데이터(서울) 백필
UPDATE weather_data SET city = 'SEOUL' WHERE city IS NULL;
UPDATE weather_data SET city_name = '서울' WHERE city_name IS NULL;
UPDATE weather_data SET country = '한국' WHERE country IS NULL;

ALTER TABLE weather_data ALTER COLUMN city SET NOT NULL;
ALTER TABLE weather_data ALTER COLUMN city_name SET NOT NULL;
ALTER TABLE weather_data ALTER COLUMN country SET NOT NULL;

CREATE INDEX IF NOT EXISTS idx_weather_city ON weather_data(city);
CREATE INDEX IF NOT EXISTS idx_weather_city_fetched ON weather_data(city, fetched_at DESC);

COMMENT ON COLUMN weather_data.city IS '도시 코드 (City enum name)';
COMMENT ON COLUMN weather_data.city_name IS '도시 한글 이름';
COMMENT ON COLUMN weather_data.country IS '국가 이름';

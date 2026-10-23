import unittest
from test_piper_runtime_server import load_server

class PiperPronunciationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.server=load_server()

    def test_price_date_units_preserve_values_without_an_llm(self):
        f=self.server.normalize_korean_speech_text
        self.assertEqual(f('2026-10-19, 14,595.00 USD/t, +56달러, 3.5kg, 0.39%'),
            '이천이십육년 시월 십구일, 일만 사천오백구십오 점 영영 달러 퍼 톤, 플러스 오십육 달러, 삼 점 오 킬로그램, 영 점 삼구 퍼센트')
        self.assertEqual(f('2026년 6월 1일'), '이천이십육년 유월 일일')
        self.assertEqual(f('같이 국물이 꽃잎 읽는 좋습니다'), '같이 국물이 꽃잎 읽는 좋습니다')

    def test_ambiguous_ids_invalid_dates_and_large_numbers_stay_unchanged(self):
        f=self.server.normalize_korean_speech_text
        for value in ['v3.5 build123 010-1234-5678','2026-02-30','1,23 USD','001kg','1234567890123456원','model3kg']:
            self.assertEqual(f(value),value)

    def test_candidate_dictionary_is_opt_in_and_does_not_rewrite_compounds(self):
        f=self.server.apply_korean_pronunciation_profile
        self.assertEqual(f('국물이 읽는 신라', 'standard'), '국물이 읽는 신라')
        self.assertEqual(f('국물이 읽는 신라', 'candidate-v1'), '궁무리 잉는 실라')
        self.assertEqual(f('신라면', 'candidate-v1'), '신라면')
        with self.assertRaises(ValueError): f('국물이', 'unreviewed')

    def test_normalization_is_idempotent_and_called_by_speech_preparation(self):
        source='2026-10-19 3kg 56달러'
        normalized,mode=self.server.prepare_synthesis_text(source)
        self.assertEqual(mode,'korean-normalized')
        self.assertEqual(self.server.prepare_synthesis_text(normalized)[0],normalized)
        self.assertEqual(source,'2026-10-19 3kg 56달러')

if __name__=='__main__':unittest.main()

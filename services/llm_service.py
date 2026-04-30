"""
Okwis AI - LLM Service
AI Provider yönetimi (Gemini, DeepSeek, Claude)

Bu modül app.py'den extract edilmiştir.
Backward compatibility için app.py'de wrapper fonksiyonlar kalacak.
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# Global client cache
_deepseek_client = None
_claude_client = None


class LLMService:
    """
    AI Provider yönetimi ve metin üretimi
    
    Desteklenen provider'lar:
    - Gemini (Google) - Ücretsiz, rate limit var
    - DeepSeek - Ücretli, ucuz
    - Claude (Anthropic) - Ücretli, premium
    """
    
    def __init__(self):
        """LLM Service başlat"""
        self.gemini_keys = self._load_gemini_keys()
        self.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
        self.deepseek_base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").strip()
        self.deepseek_model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat").strip()
        self.claude_api_key = os.getenv("CLAUDE_API_KEY", "").strip()
        self.claude_model = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022").strip()
        
        # Provider seçimi
        self.ai_provider = os.getenv("AI_PROVIDER", "gemini").strip().lower()
        self.ai_fallback_gemini = os.getenv("AI_FALLBACK_GEMINI", "true").lower() == "true"
        self.ai_fallback_deepseek = os.getenv("AI_FALLBACK_DEEPSEEK", "true").lower() == "true"
    
    def _load_gemini_keys(self) -> list[str]:
        """
        Gemini API key'lerini yükle
        
        Sıra:
        1. GEMINI_API_KEYS (virgülle ayrılmış)
        2. GEMINI_API_KEY, GEMINI_API_KEY_2, ..., GEMINI_API_KEY_10
        
        Returns:
            Benzersiz key listesi
        """
        keys = []
        seen = set()
        
        # GEMINI_API_KEYS (virgülle ayrılmış)
        bulk = os.getenv("GEMINI_API_KEYS", "").strip()
        if bulk:
            for key in bulk.split(","):
                k = key.strip()
                if k and k not in seen:
                    seen.add(k)
                    keys.append(k)
        
        # GEMINI_API_KEY, _2, _3, ..., _10
        for i in range(1, 11):
            suffix = "" if i == 1 else f"_{i}"
            key = os.getenv(f"GEMINI_API_KEY{suffix}", "").strip()
            if key and key not in seen:
                seen.add(key)
                keys.append(key)
        
        return keys
    
    def _get_deepseek_client(self):
        """DeepSeek client'ı lazy load"""
        global _deepseek_client
        
        if _deepseek_client is None:
            if not self.deepseek_api_key:
                raise RuntimeError("DEEPSEEK_API_KEY eksik")
            
            try:
                from openai import OpenAI
            except ModuleNotFoundError as e:
                raise ModuleNotFoundError(
                    "openai paketi yüklü değil. pip install openai"
                ) from e
            
            _deepseek_client = OpenAI(
                api_key=self.deepseek_api_key,
                base_url=self.deepseek_base_url
            )
        
        return _deepseek_client
    
    def _get_claude_client(self):
        """Claude client'ı lazy load"""
        global _claude_client
        
        if _claude_client is None:
            if not self.claude_api_key:
                raise RuntimeError("CLAUDE_API_KEY tanımlı değil")
            
            try:
                import anthropic
            except ModuleNotFoundError as e:
                raise ModuleNotFoundError(
                    "anthropic paketi yüklü değil. pip install anthropic"
                ) from e
            
            _claude_client = anthropic.Anthropic(api_key=self.claude_api_key)
        
        return _claude_client
    
    def _is_quota_error(self, exc: BaseException) -> bool:
        """Kota/rate limit hatası mı?"""
        msg = str(exc).lower()
        return any(k in msg for k in [
            "429", "quota", "resource exhausted",
            "rate", "limit", "503", "overloaded"
        ])
    
    def _is_auth_error(self, exc: BaseException) -> bool:
        """Authentication hatası mı?"""
        msg = str(exc).lower()
        return any(k in msg for k in [
            "401", "invalid", "incorrect", "unauthorized",
            "authentication", "invalid x-api-key"
        ])
    
    def _is_payment_error(self, exc: BaseException) -> bool:
        """Ödeme/bakiye hatası mı?"""
        msg = str(exc).lower()
        return any(k in msg for k in [
            "402", "403", "insufficient", "balance",
            "billing", "payment", "credit", "exceeded"
        ])
    
    def generate_with_gemini(self, prompt: str) -> str:
        """
        Gemini ile metin üret (tüm key'leri dene)
        
        Args:
            prompt: Prompt metni
        
        Returns:
            Üretilen metin
        
        Raises:
            RuntimeError: Tüm key'ler başarısız
        """
        if not self.gemini_keys:
            raise RuntimeError(
                "GEMINI_API_KEY (veya GEMINI_API_KEY_2 / _3 / GEMINI_API_KEYS) tanımlı değil"
            )
        
        try:
            import google.generativeai as genai
        except ModuleNotFoundError as e:
            raise ModuleNotFoundError(
                "google-generativeai paketi yüklü değil. pip install google-generativeai"
            ) from e
        
        last_error = None
        
        for idx, key in enumerate(self.gemini_keys):
            try:
                genai.configure(api_key=key)
                model = genai.GenerativeModel("gemini-2.5-flash-lite")
                response = model.generate_content(prompt)
                text = getattr(response, "text", None) or ""
                text = str(text).strip()
                
                if not text:
                    raise RuntimeError("Model boş yanıt döndü")
                
                return text
            
            except Exception as e:
                last_error = e
                
                # Kota hatası ve başka key varsa devam et
                if idx < len(self.gemini_keys) - 1 and self._is_quota_error(e):
                    logger.warning(
                        "Gemini anahtar %s/%s başarısız (kota vb.), sıradaki deneniyor: %s",
                        idx + 1,
                        len(self.gemini_keys),
                        e,
                    )
                    continue
                
                # Son key veya kota hatası değil, hemen raise et
                raise
        
        # Tüm key'ler tükendi
        if last_error:
            raise last_error
        
        raise RuntimeError("Gemini yanıt üretilemedi")
    
    def generate_with_deepseek(self, prompt: str) -> str:
        """
        DeepSeek ile metin üret
        
        Args:
            prompt: Prompt metni
        
        Returns:
            Üretilen metin
        """
        client = self._get_deepseek_client()
        
        response = client.chat.completions.create(
            model=self.deepseek_model,
            messages=[{"role": "user", "content": prompt}],
        )
        
        choice = (response.choices or [None])[0]
        msg = choice.message if choice else None
        text = (getattr(msg, "content", None) or "") if msg else ""
        text = str(text).strip()
        
        if not text:
            raise RuntimeError("Model boş yanıt döndü")
        
        return text
    
    def generate_with_claude(self, prompt: str) -> str:
        """
        Claude ile metin üret
        
        Args:
            prompt: Prompt metni
        
        Returns:
            Üretilen metin
        """
        client = self._get_claude_client()
        
        message = client.messages.create(
            model=self.claude_model,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        
        text = ""
        for block in (message.content or []):
            if hasattr(block, "text"):
                text += block.text
        
        text = text.strip()
        
        if not text:
            raise RuntimeError("Model boş yanıt döndü")
        
        return text
    
    def generate(
        self,
        prompt: str,
        provider: Optional[str] = None,
        fallback: bool = True,
        user_plan: Optional[str] = None
    ) -> str:
        """
        Metin üret (provider seçimi + fallback)
        
        Args:
            prompt: Prompt metni
            provider: "gemini", "deepseek", "claude" (None = otomatik)
            fallback: Başarısız olursa diğer provider'ları dene
            user_plan: Kullanıcı planı ("free", "pro", "claude")
        
        Returns:
            Üretilen metin
        
        Raises:
            Exception: Tüm provider'lar başarısız
        """
        # Provider seçimi
        if provider is None:
            # Kullanıcı planına göre seç
            if user_plan == "claude" and self.claude_api_key:
                provider = "claude"
            elif self.ai_provider == "deepseek":
                provider = "deepseek"
            else:
                provider = "gemini"
        
        # Ana provider'ı dene
        try:
            if provider == "claude":
                return self.generate_with_claude(prompt)
            elif provider == "deepseek":
                return self.generate_with_deepseek(prompt)
            else:  # gemini
                return self.generate_with_gemini(prompt)
        
        except Exception as e:
            logger.error(f"{provider} başarısız: {e}")
            
            if not fallback:
                raise
            
            # Fallback stratejisi
            if provider == "claude":
                # Claude başarısız → Gemini dene (auth hatası değilse)
                if not self._is_auth_error(e) and self.gemini_keys:
                    logger.warning("Claude başarısız, Gemini'ye düşülüyor: %s", e)
                    try:
                        return self.generate_with_gemini(prompt)
                    except Exception as e2:
                        logger.error("Gemini fallback başarısız: %s", e2)
                        # DeepSeek dene
                        if self.ai_fallback_deepseek and self.deepseek_api_key:
                            logger.warning("Gemini başarısız, DeepSeek deneniyor")
                            return self.generate_with_deepseek(prompt)
                        raise
                raise
            
            elif provider == "deepseek":
                # DeepSeek başarısız → Gemini dene (ödeme hatası değilse)
                if (self.ai_fallback_gemini and self.gemini_keys and
                    (self._is_payment_error(e) or self._is_quota_error(e))):
                    logger.warning("DeepSeek başarısız, Gemini'ye düşülüyor: %s", e)
                    return self.generate_with_gemini(prompt)
                raise
            
            else:  # gemini
                # Gemini başarısız → DeepSeek dene
                if self.ai_fallback_deepseek and self.deepseek_api_key:
                    logger.warning("Gemini başarısız, DeepSeek deneniyor: %s", e)
                    try:
                        return self.generate_with_deepseek(prompt)
                    except ModuleNotFoundError as ie:
                        logger.error("DeepSeek için openai gerekli: %s", ie)
                        raise e from ie
                raise


# ─── Global Instance (Singleton) ───────────────────────────────────────────

_llm_service_instance: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """
    LLM service singleton
    
    Returns:
        LLMService instance
    """
    global _llm_service_instance
    
    if _llm_service_instance is None:
        _llm_service_instance = LLMService()
    
    return _llm_service_instance


# ─── Backward Compatibility (app.py için) ──────────────────────────────────

def llm_metin_uret(prompt: str, user_id: Optional[int] = None) -> str:
    """
    Backward compatibility wrapper
    
    Eski API: llm_metin_uret(prompt, user_id)
    Yeni API: get_llm_service().generate(prompt, user_plan=...)
    
    Args:
        prompt: Prompt metni
        user_id: Kullanıcı ID (plan tespiti için)
    
    Returns:
        Üretilen metin
    """
    service = get_llm_service()
    
    # Kullanıcı planını tespit et (app.py'den import etmeden)
    user_plan = None
    if user_id is not None:
        try:
            # app.py'deki _kullanici_plan_bilgisi fonksiyonunu kullan
            # (circular import'u önlemek için dinamik import)
            import app
            if hasattr(app, '_kullanici_plan_bilgisi'):
                plan_info = app._kullanici_plan_bilgisi(user_id)
                user_plan = plan_info.get("plan")
        except Exception as e:
            logger.warning(f"Kullanıcı planı tespit edilemedi: {e}")
    
    return service.generate(prompt, user_plan=user_plan, fallback=True)


# ─── Test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Basit test
    print("=" * 60)
    print("LLM Service Test")
    print("=" * 60)
    
    service = get_llm_service()
    
    print(f"\nGemini keys: {len(service.gemini_keys)}")
    print(f"DeepSeek key: {'✅' if service.deepseek_api_key else '❌'}")
    print(f"Claude key: {'✅' if service.claude_api_key else '❌'}")
    print(f"AI Provider: {service.ai_provider}")
    
    # Test prompt
    test_prompt = "Merhaba! Kısa bir test mesajı yaz (1 cümle)."
    
    try:
        print(f"\nTest prompt: {test_prompt}")
        result = service.generate(test_prompt)
        print(f"✅ Sonuç: {result}")
    except Exception as e:
        print(f"❌ Hata: {e}")

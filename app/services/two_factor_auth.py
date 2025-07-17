import pyotp
import qrcode
import io
import base64
from typing import Optional
import secrets

class TwoFactorAuthService:
    def __init__(self):
        self.app_name = "SecureTradeAPI"
        self.issuer = "SecureTradeAPI"
    
    def generate_secret(self) -> str:
        return pyotp.random_base32()
    
    def generate_qr_code(self, email: str, secret: str) -> str:
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(
            name=email,
            issuer_name=self.issuer
        )
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        img_str = base64.b64encode(buffer.getvalue()).decode()
        return f"data:image/png;base64,{img_str}"
    
    def verify_token(self, secret: str, token: str) -> bool:
        try:
            totp = pyotp.TOTP(secret)
            return totp.verify(token, valid_window=1)
        except:
            return False
    
    def generate_backup_codes(self, count: int = 10) -> list:
        codes = []
        for _ in range(count):
            code = secrets.token_hex(4).upper()
            codes.append(f"{code[:4]}-{code[4:]}")
        return codes
    
    def get_current_token(self, secret: str) -> str:
        totp = pyotp.TOTP(secret)
        return totp.now()

two_factor_service = TwoFactorAuthService()
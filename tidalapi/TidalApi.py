import pkce
import requests
from config import *

class TidalApi:
  headers = {}
  params = {}
  code = ""
  csrf_token = ""
    
  def __init__(self):
    self.code_verifier, self.code_challenge = self._generate_pkce_code()
    self.headers = {
      "accept": "application/json, text/plain, */*",
      "content-type": "application/json",
    }
    self.params = {
      'appMode': 'WEB',
      'client_id': 'CzET4vdadNUFQ5JU',
      'redirect_uri': 'https://listen.tidal.com/login/auth',
      'response_type': 'code',
      'restrictSignup': 'true',
      'scope': 'r_usr w_usr',
      "code_challenge_method": "S256",
      "code_challenge": self.code_challenge
    }
    self.s = requests.Session()
    self.csrf_token = ""
    self.s.headers = {**self.headers, "user-agent": USER_AGENT, "origin": ORIGIN}
    
  def _generate_pkce_code(self):
    code_verifier = pkce.generate_code_verifier(length=128)
    code_challenge = pkce.get_code_challenge(code_verifier)
    return code_verifier, code_challenge
    
  def _load_session(self):    
    res = self.s.get(f"{BASE_LOGIN_URI}/authorize", params=self.params)
    
    # TODO: add captha bypass 
    
    csrf_token = res.headers['Set-Cookie'].split("_csrf-token=")[1].split(";")[0]
    
    if csrf_token:
      self.csrf_token = csrf_token
      self.headers.update({"x-csrf-token": self.csrf_token})
      self.s.headers.update({"x-csrf-token": self.csrf_token})
      
    # TODO: Add some clean logs
    
  def _check_existing_user(self, email):
    if not self.csrf_token:
      self._load_session()
    
    res = self.s.post(f"{BASE_LOGIN_URI}/api/email", params=self.params, json={"email": "jaki99kofficial@gmail.com", "recaptchaResponse": ""})
    
    if res.status_code == 200:
      return res.json()["isValidEmail"]
    return False
      
    
  def _authorize(self, email, password):
    existing = self._check_existing_user(email)
    
    if existing:
      res = self.s.post(f"{BASE_LOGIN_URI}/api/email/user/existing", params=self.params, json={"email": "jaki99kofficial@gmail.com", "password": "Camillo01_"})
      code = res.json()["redirectUri"].split("code=")[1].split("&")[0]
      self.code = code
      
  def login(self, email, password):
    if not self.code:
      self._authorize(email, password)
    
    payload = {
      "client_id": "CzET4vdadNUFQ5JU",
      # TODO: for client unique key use uid4 generation ?
      "code": self.code,
      "grant_type": "authorization_code",
      "redirect_uri": "https://listen.tidal.com/login/auth",
      "scope": "r_usr w_usr",
      "code_verifier": self.code_verifier
    }
    
    print("response")
    res = self.s.post(f"{BASE_LOGIN_URI}/oauth2/token", json=payload)
    
    print(res.json())
    
    
t = TidalApi()
t.login("", "")

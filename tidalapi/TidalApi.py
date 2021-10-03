from config import *
import os, json, pkce, requests

# NOTE: see pkce specification here
# https://datatracker.ietf.org/doc/html/rfc7636#page-17

class TidalApi:
  headers = {}
  params = {}
  code = ""
  csrf_token = ""
  access_token = ""
  refresh_token = ""
    
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
    
  def _get_page(self, page_name="home", params={}):
    params = {**params, "countryCode": "EN", "deviceType": "BROWSER"}
    response = self.s.get(f"{BASE_LISTEN_API}/pages/{page_name}", params=params)
    return response.json()

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
      
  def _write_local_cache(self, data, filename="./.user-cache.json"):
    with open(filename, "w") as output_file:
      json.dump(data, output_file)
      return True
    return False

  def _check_local_cache(self, filename="./.user-cache.json"):
    op_status = False
    if os.path.exists(filename):
      with open(filename, "r") as cache_file:
        try:
          data_string = cache_file.read()
          data_json = json.loads(data_string)
          if "access_token" in data_json.keys() and "refresh_token" in data_json.keys():
            self.access_token = data_json["access_token"]
            self.refresh_token = data_json["refresh_token"]
            op_status = True
        except:
          op_status = False
    return op_status

  def login(self, email, password):

    if not self._check_local_cache():
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
      
      res = self.s.post(f"{BASE_LOGIN_URI}/oauth2/token", json=payload)
      json_data = res.json()

      self.access_token = json_data["access_token"]
      self.refresh_token = json_data["refresh_token"]

      file_created = self._write_local_cache(data=json_data)

      if file_created:
        print("Cache file written filesystem")
      else:
        print("Error while creating local cache file")
      
      # TODO: add check if login is successfull or not (maybe boolean)
    else:
      # TODO: find out how to get new token starting from refresh_token
      print("Logged in from local cache")
    self.s.headers.update({"authorization": f"Bearer {self.access_token}"})
  # TODO: create request function to make all api calls

  # --- ME AND DEVICES ---

  def me(self):
    res = self.s.get(f"{BASE_LOGIN_URI}/oauth2/me")
    
    if "application/json" in res.headers.get("content-type"):
      return res.json()
    else:
      return res.content

  def get_clients(self):
    res = self.s.get(f"{BASE_LISTEN_API}/users/182349322/clients")
    return res.json()

  # --- PLAYLISTS ---

  def create_playlist(self,
                      name="Your Playlist",
                      description="Created with Tidal Wrapper",
                      folder="root"):
      params = {"name": name, "description": description, "folderId": folder}
      response = self.s.put(f"{BASE_API}/my-collection/playlists/folders/create-playlist", params=params)
      return response.status_code == 200

  def get_playlists(self):
    params = {
      "folderId": "root",
      "offset": "0",
      "limit": "50",
      "order": "DATE",
      "orderDirection": "DESC",
      "countryCode": "IT",
      "locale": "it_IT",
      "deviceType": "BROWSER"
    }
    res = self.s.get(f"{BASE_API}/my-collection/playlists/folders", params=params)
    return res.json()

  def update_playlist(self, update_data={}, playlist_id=None):
    if playlist_id:
      headers = {**self.s.headers, "content-type": "application/x-www-form-urlencoded; charset=UTF-8"}
      res = self.s.post(f"{BASE_LISTEN_API}/playlists/{playlist_id}", data=update_data, headers=headers)
      return res.status_code == 200
    else:
      return False
    return False

  def delete_playlist(self, playlist_id=None):
    if playlist_id:
      params = {"trns": f"trn:playlist:{playlist_id}"}
      res = self.s.put(f"{BASE_API}/my-collection/playlists/folders/remove", params=params)
      if res.status_code == 204:
        return True
      else:
        return False
    return False

  def get_homepage(self, country_code="EN"):
    response = self._get_page("home")
    return response

  # TODO: make variables such as countryCode globals variables
  # that u can set when instantiating the class such as **options
  def get_album(self, album_id=None):
    response = self._get_page("album", {"albumId": album_id})
    return response

  def search(self, query=None, **params):
    if not params:
      params = {
        "limit": "25",
        "offset": 0,
        "types": ["ARTISTS","ALBUMS","TRACKS","VIDEOS","PLAYLISTS"],
        "includeContributors": "true",
        "locale": "en_US",
        "countryCode": "EN",
        "query": query,
        "deviceType": "BROWSER"
      }
    response = self.s.get(f"{BASE_LISTEN_API}/search/top-hits", params=params)
    return response.json()

  def get_artist(self, artist_id=None):
    response = self._get_page("artist", {"artistId": artist_id})
    return response

  def get_user_mixes(self):
    response = self._get_page("my_collection_my_mixes")
    return response

t = TidalApi()
t.login("", "")
print(t.get_homepage())
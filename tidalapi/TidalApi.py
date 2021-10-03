from config import *
import os, json, pkce, requests

# NOTE: see pkce specification here
# https://datatracker.ietf.org/doc/html/rfc7636#page-17

class TidalApi:
  code = ""
  user_id = ""
  headers = {}
  params = {}
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
    self.s.headers = {**self.headers, "user-agent": USER_AGENT, "origin": ORIGIN}
    
  def _generate_pkce_code(self):
    code_verifier = pkce.generate_code_verifier(length=128)
    code_challenge = pkce.get_code_challenge(code_verifier)
    return code_verifier, code_challenge
    
  def _get_page(self, page_name="home", params={}):
    params = {**params, "countryCode": "EN", "deviceType": "BROWSER"}
    response = self._request(url=f"{BASE_LISTEN_API}/pages/{page_name}", payload=params)
    return response

  def _request(self, url=f"{BASE_LISTEN_API}", method="GET", headers={}, params={}, data={}, json=True):
    response = None
    headers = {**self.headers, **headers}
    request_info = {"url": url, "headers": headers}

    if method == "GET":
      response = self.s.get(**request_info, params=params)
    elif method == "POST":
      if len(data.keys()) > 0:
        request_info = {"json": data, **request_info} if json else {"data": data, **request_info}
      response = self.s.post(**request_info, params=params)
    elif method == "PUT":
      if len(data.keys()) > 0:
        request_info = {"json": data, **request_info} if json else {"data": data, **request_info}
      response = self.s.put(**request_info, params=params)

    return response

  def _load_session(self):    
    res = self._request(f"{BASE_LOGIN_URI}/authorize", params=self.params)

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
    
    data = {"email": email, "recaptchaResponse": ""}
    res = self._request(f"{BASE_LOGIN_URI}/api/email", params=self.params, data=data, method="POST")

    if res.status_code == 200:
      return res.json()["isValidEmail"]
    return False
      
    
  def _authorize(self, email, password):
    existing = self._check_existing_user(email)
    
    if existing:
      data = {"email": email, "password": password}
      res = self._request(f"{BASE_LOGIN_URI}/api/email/user/existing", params=self.params, data=data, method="POST")
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
            self.access_token = data_json.get("access_token")
            self.refresh_token = data_json.get("refresh_token")
            self.user_id = data_json.get("user").get("userId")
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
      
      # res = self._request(f"{BASE_LOGIN_URI}/oauth2/token", data=pyaload)
      response = self._request(f"{BASE_LOGIN_URI}/oauth2/token", data=payload, method="POST").json()

      self.access_token = response.get("access_token")
      self.refresh_token = response.get("refresh_token")
      self.user_id = response.get("user").get("userId")

      self._write_local_cache(data=response)      
      # TODO: add check if login is successfull or not (maybe boolean)
      # TODO: find out how to get new token starting from refresh_token
    self.s.headers.update({"authorization": f"Bearer {self.access_token}"})
  # TODO: create request function to make all api calls

  # --- ME AND DEVICES ---

  def me(self):
    res = self._request(url=f"{BASE_LOGIN_URI}/oauth2/me").json()
    return res

  def get_user_mixes(self):
    response = self._get_page("my_collection_my_mixes").json()
    return response

  def get_clients(self):
    # TODO: put variables instead of hard-coded value -> 182349322
    res = self._request(f"{BASE_LISTEN_API}/users/{self.user_id}/clients").json()
    return res

  def get_homepage(self, country_code="EN"):
    response = self._get_page("home").json()
    return response

  def get_playlists(self, **params):
    if not params:
      params = {
        "folderId": "root",
        "offset": "0",
        "limit": "50",
        "order": "DATE",
        "orderDirection": "DESC",
        "countryCode": "EN",
        "locale": "en_EN",
        "deviceType": "BROWSER"
      }
    res = self._request(f"{BASE_API}/my-collection/playlists/folders", payload=params).json()
    return res

  # --- PLAYLISTS ---

  def create_playlist(self,
                      name="Your Playlist",
                      description="Created with Tidal Wrapper",
                      folder="root"):
      params = {"name": name, "description": description, "folderId": folder}
      response = self._request(url=f"{BASE_API}/my-collection/playlists/folders/create-playlist", method="PUT", params=params).json()
      return response


  def update_playlist(self, playlist_id=None, update_data={}):
    if playlist_id:
      headers = {"content-type": "application/x-www-form-urlencoded; charset=UTF-8"}
      response = self._request(f"{BASE_LISTEN_API}/playlists/{playlist_id}", method="POST", data=update_data, headers=headers, json=False)
      return response.status_code == 200
    else:
      return False
    return False

  def delete_playlist(self, playlist_id=None):
    if playlist_id:
      params = {"trns": f"trn:playlist:{playlist_id}"}
      res = self._request(f"{BASE_API}/my-collection/playlists/folders/remove", params=params, method="PUT")
      if res.status_code == 204:
        return True
      else:
        return False
    return False

  # --- ALBUMS ---

  # TODO: make variables such as countryCode globals variables
  # that u can set when instantiating the class such as **options
  def get_album(self, album_id=None):
    response = self._get_page("album", {"albumId": album_id})
    return response

  # --- SEARCH ---

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
    response = self._request(f"{BASE_LISTEN_API}/search/top-hits", params=params)
    return response.json()

  # --- ARTISTS ---

  def get_artist(self, artist_id=None):
    response = self._get_page("artist", {"artistId": artist_id})
    return response

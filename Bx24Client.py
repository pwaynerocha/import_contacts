#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Wrapper over Bitrix24 cloud API"""

from json import loads
from logging import info
from time import sleep
from requests import adapters, post, exceptions, Response
from multidimensional_urlencode import urlencode
import urllib.parse
from logger import write_log

# Retries for API request
adapters.DEFAULT_RETRIES = 10


class Bitrix24(object):
    """Class for working with Bitrix24 cloud API"""

    # Bitrix24 API endpoint
    api_url = "https://%s/rest/%s.json"
    # Bitrix24 oauth server
    oauth_url = "https://oauth.bitrix.info/oauth/token/"
    # Timeout for API request in seconds
    timeout = 60

    log = True
    log_mode = "verbose"
    
    def __init__(
        self, domain, auth_token, refresh_token="", client_id="", client_secret="", token_renew_callback=None):
        """Create Bitrix24 API object
        :param domain: str Bitrix24 domain
        :param auth_token: str Auth token
        :param refresh_token: str Refresh token
        :param client_id: str Client ID for refreshing access tokens
        :param client_secret: str Client secret for refreshing access tokens
        """
        self.domain = domain
        self.auth_token = auth_token
        self.refresh_token = refresh_token
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_renew_callback = token_renew_callback

    def call(self, method, params1=None, params2=None, params3=None, params4=None):
        """Call Bitrix24 API method
        :param method: Method name
        :param params1: Method parameters 1
        :param params2: Method parameters 2. Needed for methods with determinate consequence of parameters
        :param params3: Method parameters 3. Needed for methods with determinate consequence of parameters
        :param params4: Method parameters 4. Needed for methods with determinate consequence of parameters
        :return: Call result
        """
        if method == "" or not isinstance(method, str):
            raise Exception("Empty Method")

        if method == "batch" and "prepared" not in params1:
            params1["cmd"] = self.prepare_batch(params1["cmd"])
            params1["prepared"] = True

        encoded_parameters = ""

        for i in [params1, params2, params3, params4, {"auth": self.auth_token}]:
            if i is not None:
                if "cmd" in i:
                    i = dict(i)
                    encoded_parameters += (
                        self.encode_cmd(i["cmd"])
                        + "&"
                        + urlencode({"halt": i["halt"]})
                        + "&"
                    )
                else:
                    encoded_parameters += self.http_build_query(i) + "&"

        r = {}

        try:
            # request url
            url = self.api_url % (self.domain, method)
            # Make API request
            r = post(url, data=encoded_parameters, timeout=self.timeout)
            # Decode response
            result = loads(r.text)
        except ValueError:
            result = dict(error="Error on decode api response [%s]" % r.text)
        except exceptions.ReadTimeout:
            result = dict(error="Timeout waiting expired [%s sec]" % str(self.timeout))
        except exceptions.ConnectionError:
            result = dict(
                error="Max retries exceeded [" + str(adapters.DEFAULT_RETRIES) + "]"
            )
        
        if "error" in result and result["error"] in ("NO_AUTH_FOUND", "expired_token"):
            result = self.refresh_tokens()

            self._print_result(r)

            if result is not True:
                return result
            # Repeat API request after renew token
            result = self.call(method, params1, params2, params3, params4)
        elif result.get("error_description", ""):
            self._print_result(result.get("error_description", ""))
            
            return result
        elif "error" in result and result["error"] in "QUERY_LIMIT_EXCEEDED":
            # Suspend call on two second, wait for expired limitation time by Bitrix24 API
            sleep(2)
            return self.call(method, params1, params2, params3, params4)
        
        self._print_result(r)
        
        return result

    # https://stackoverflow.com/a/39082010/12354388
    def http_build_query(self, data):
        parents = list()
        pairs = dict()

        def renderKey(parents):
            depth, outStr = 0, ""
            for x in parents:
                s = "[%s]" if depth > 0 or isinstance(x, int) else "%s"
                outStr += s % str(x)
                depth += 1
            return outStr

        def r_urlencode(data):
            if isinstance(data, list) or isinstance(data, tuple):
                for i in range(len(data)):
                    parents.append(i)
                    r_urlencode(data[i])
                    parents.pop()
            elif isinstance(data, dict):
                for key, value in data.items():
                    parents.append(key)
                    r_urlencode(value)
                    parents.pop()
            else:
                pairs[renderKey(parents)] = str(data)

            return pairs

        return urllib.parse.urlencode(r_urlencode(data))

    def refresh_tokens(self):
        """Refresh access tokens
        :return:
        """
        r = {}
        try:
            # Make call to oauth server
            r = post(
                self.oauth_url,
                params={
                    "grant_type": "refresh_token",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": self.refresh_token,
                },
            )

            self._print_result(r)
            
            result = loads(r.text)
            # Renew access tokens
            self.auth_token = result["access_token"]
            self.refresh_token = result["refresh_token"]
            if callable(self.token_renew_callback):
                try:
                    self._print_result("running token renew callback")
                    self.token_renew_callback(result["access_token"], result["refresh_token"], result["expires"], result["expires_in"])
                except Exception as e:
                    self._print_result(e)
                    info(["Error executing token renew callback", str(e)])
            
            self._print_result(["Tokens", self.auth_token, self.refresh_token])
            info(["Tokens", self.auth_token, self.refresh_token])
            return True
        except (ValueError, KeyError):
            result = dict(error="Error on decode oauth response [%s]" % r.text)
            return result

    def get_tokens(self):
        """Get access tokens
        :return: dict
        """
        return {"auth_token": self.auth_token, "refresh_token": self.refresh_token}

    @staticmethod
    def prepare_batch(params):
        """
        Prepare methods for batch call
        :param params: dict
        :return: dict
        """
        if not isinstance(params, dict):
            raise Exception("Invalid 'cmd' structure")

        batched_params = dict()

        for call_id in sorted(params.keys()):
            if not isinstance(params[call_id], list):
                raise Exception("Invalid 'cmd' method description")
            method = params[call_id].pop(0)
            if method == "batch":
                raise Exception("Batch call cannot contain batch methods")
            temp = ""
            for i in params[call_id]:
                temp += urlencode(i) + "&"
            batched_params[call_id] = method + "?" + temp

        return batched_params

    @staticmethod
    def encode_cmd(cmd):
        """Resort batch cmd by request keys and encode it
        :param cmd: dict List methods for batch request with request ids
        :return: str
        """
        cmd_encoded = ""

        for i in sorted(cmd.keys()):
            cmd_encoded += urlencode({"cmd": {i: cmd[i]}}) + "&"

        return cmd_encoded

    def batch(self, params):
        """Batch calling without limits. Method automatically prepare method for batch calling
        :param params:
        :return:
        """
        if "halt" not in params or "cmd" not in params:
            return dict(error="Invalid batch structure")

        result = dict()

        result["result"] = dict(
            result_error={},
            result_total={},
            result={},
            result_next={},
        )
        count = 0
        batch = dict()
        for request_id in sorted(params["cmd"].keys()):
            batch[request_id] = params["cmd"][request_id]
            count += 1
            if len(batch) == 49 or count == len(params["cmd"]):
                temp = self.call("batch", {"halt": params["halt"], "cmd": batch})
                for i in temp["result"]:
                    if len(temp["result"][i]) > 0:
                        result["result"][i] = self.merge_two_dicts(
                            temp["result"][i], result["result"][i]
                        )
                batch = dict()

        return result

    @staticmethod
    def merge_two_dicts(x, y):
        """Given two dicts, merge them into a new dict as a shallow copy."""
        z = x.copy()
        z.update(y)
        return z

    def _print_result(self, response):
        try:
            if isinstance(response, Response):
                color = (
                    31
                    if response.status_code in [500, 401, 404]
                    or response.status_code >= 400
                    else 32
                )

                if self.log_mode == "log":
                    write_log("bitrix", f"{response.request.method.upper()} [{response.status_code}] | [{response.url}]\n{response.content}\n")
                elif self.log_mode == "minimal":
                    print(f"\n\033[96m[Bitrix24]\033[0m \033[1;{color}m{response.request.method.upper()} [{response.status_code}]\033[1;37m | \033[3m[{response.url}]")
                elif self.log_mode == "verbose":
                    print("\n\033[96m[Bitrix24]\033[0m")
                    print(f"\033[1;{color}m{response.request.method.upper()} [{response.status_code}]\033[1;37m | \033[3m[{response.url}][body]\033[0m\n\033[1mRESPONSE:\033[0m\n{response.content}\n")
            else:
                if self.log_mode == "log":
                    write_log("bitrix", f"{response.request.method.upper()} [{response.status_code}] | [{response.url}]\n{response.content}\n")
                    write_log("bitrix", response)
                else:
                    print("\n\033[96m[Bitrix24]\033[0m")
                    print(f"\033[1mRESPONSE:\033[0m\n{response}\n")
        except Exception as e:
            print("\n\033[96m[Bitrix24] not possible to print Response:\033[0m")
            print(str(e))
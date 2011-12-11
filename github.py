import http.client
import os.path
import json

from collections import OrderedDict
from subprocess import Popen, PIPE

class Github:
	def __init__(self, token, user):
		self.token = token
		self.user = user
		self.make_subclasses()

		self.conn = None
		self.get_connection()

	def make_subclasses(self):
		self.repos = Repos(self)

	def get_connection(self):
		# TODO cert check
		if not self.conn:
			self.conn = http.client.HTTPSConnection("api.github.com")

	'''
	def authenticate(self):
		self.get_connection()
		self.conn.request("GET", "", None, self.get_auth_headers())
		res = self.conn.getresponse()
		print(res.msg)
		res.read()
		
		self.conn.request("GET", "/authorizations", None, self.get_auth_headers())
		res = self.conn.getresponse()
		print(json.loads(res.read().decode()))
		#return res.status == 204
	'''

	def get_auth_headers(self):
		return {
			"Authorization": "token %s" % self.token
		}

class _Subclass:
	def __init__(self, parent):
		self.parent = parent

class Repos(_Subclass):
	def list_downloads(self, repo):
		user = self.parent.user
		self.parent.conn.request("GET", "/repos/%s/%s/downloads" % (user, repo),
				None, self.parent.get_auth_headers())
		res = self.parent.conn.getresponse()
		if res.status not in (200, 404):
			raise ValueError("That bitch should be 200 or 404, but was %s." % res.status)
		return json.loads(res.read().decode())

	def get_download(self, repo, id):
		user = self.parent.user
		self.parent.conn.request("GET", "/repos/%s/%s/downloads/%s" % (user, repo, id),
				None, self.parent.get_auth_headers())
		res = self.parent.conn.getresponse()
		if res.status not in (200, 404):
			raise ValueError("That bitch should be 200 or 404, but was %s." % res.status)
		return json.loads(res.read().decode())
	
	def create_download(self, repo, fn, name, description=None, content_type=None):
		size = os.path.getsize(fn)
		user = self.parent.user
		data = {
			"name": name,
			"size": size
		}
		if description:
			data['description'] = description
		if content_type:
			data['content_type'] = content_type

		self.parent.conn.request("POST", "/repos/%s/%s/downloads" % (user, repo), 
				json.dumps(data), self.parent.get_auth_headers())
		res = self.parent.conn.getresponse()

		resource = json.loads(res.read().decode())
		headers = OrderedDict((
			("key", resource['path']),
			("acl", resource['acl']),
			("success_action_status", 201),
			("Filename", resource['name']),
			("AWSAccessKeyId", resource['accesskeyid']),
			("Policy", resource['policy']),
			("Signature", resource['signature']),
			("Content-Type", resource['mime_type']),
			("file", "@"+fn)
		))
		
		params = []
		for k, v in headers.items():
			params.append("%s=%s" % (k, v))
		cmd = "curl -F %s https://github.s3.amazonaws.com/" % (" -F ".join(params))
		cmd = cmd.split(" ")
		
		p = Popen(cmd, stdout=PIPE, stderr=PIPE, close_fds=True)
		out, err = p.communicate()
		return p.returncode == 0

	def delete_download(self, repo, id):
		user = self.parent.user
		self.parent.conn.request("DELETE", "/repos/%s/%s/downloads/%s" % (user, repo, id), 
				None, self.parent.get_auth_headers())
		res = self.parent.conn.getresponse()
		res.read()
		return res.status in (204, 404)
	
	def delete_download_by_name(self, repo, name):
		user = self.parent.user
		self.parent.conn.request("GET", "/repos/%s/%s/downloads" % (user, repo), 
				None, self.parent.get_auth_headers())
		res = self.parent.conn.getresponse()
		resource = json.loads(res.read().decode())

		id = None
		for r in resource:
			if r['name'] == name:
				id = r['id']
				break
		
		return id and self.delete_download(repo, id)
	
	def delete_all_downloads(self, repo):
		user = self.parent.user
		self.parent.conn.request("GET", "/repos/%s/%s/downloads" % (user, repo), 
				None, self.parent.get_auth_headers())
		res = self.parent.conn.getresponse()
		resource = json.loads(res.read().decode())

		for r in resource:
			self.delete_download(repo, r['id'])
		
		return True	

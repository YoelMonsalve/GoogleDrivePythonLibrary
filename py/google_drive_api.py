from __future__ import print_function
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.http import MediaFileUpload

import sys       # sys.path
import os        # os.path
import stat      # S_IRUSR
import re        # regex
from datetime import datetime
import threading
from time import sleep
from pprint import pprint

# this is to include another sources in this module
sys.path.append(os.path.dirname(__file__))
from _enum import MIME_TYPES

__author__   = "Yoel Monsalve"
__mail__     = "yymonsalve@gmail.com"
__date__     = "July, 2021"
__modified__ = "2021.08.01"
__github__   = "github.com/YoelMonsalve/GoogleDrivePythonLibrary"

"""
Requirements:

pip3 install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
"""

# If modifying these scopes, delete the file token.json.
# Q (yoel): Should it be drive.metadata only, instead of drive.metadata.readonly ???
SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly', 'https://www.googleapis.com/auth/drive']

# MIME types
MIME_TYPE_FOLDER   = MIME_TYPES.FOLDER['mime']
MIME_TYPE_FILE     = MIME_TYPES.FILE['mime']
MIME_TYPE_SHEET    = MIME_TYPES.SPREADSHEET['mime']
MIME_TYPE_DOCUMENT = MIME_TYPES.DOCUMENT['mime']
MIME_TYPE_PHOTO    = MIME_TYPES.PHOTO['mime']

class GoogleDriveAPI(object):
    """Custom class to easily manage the Google Drive API, coded in Python
    @author Yoel Monsalve
    @mail   yymonsalve@gmail.com

    References:
    ===============================================================
    https://developers.google.com/drive/api/v3/
    https://developers.google.com/drive/api/v3/quickstart/python
    https://developers.google.com/drive/api/v3/about-files
    """

    def __init__(self):
        self.name = "GoogleDriveAPI"
        self.token_file = ''        # the file containing the token, it will be generated automatically
                                    # using the authentication flow & client secret
        self.client_secret = ''     # the client secret file (download it from the Google Cloud Console page
                                    # https://console.cloud.google.com/apis/credentials?project=xxx-yyy)
        self.service = None         # the Google API service

        # MIME types
        self.MIME_TYPE_FOLDER       = MIME_TYPE_FOLDER
        self.MIME_TYPE_FILE         = MIME_TYPE_FILE
        self.MIME_TYPE_SHEET        = MIME_TYPE_SHEET
        self.MIME_TYPE_DOCUMENT     = MIME_TYPE_DOCUMENT
        self.MIME_TYPE_PHOTO        = MIME_TYPE_PHOTO

        # SCOPES
        self.SCOPES = SCOPES

    def init_service(self, scopes = []):
        """This initializes the API service, using the client authentication
        @param scopes The scopes to create the credentials for, if null then takes self.SCOPES
        """

        creds = None
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists(self.token_file):
            if scopes:
                # allows you to define other scopes each time you invoke the service
                self.SCOPES = scopes
            if not self.SCOPES:
                raise Exception(f"{self.name}.init_service failed: No SCOPE defined")
            creds = Credentials.from_authorized_user_file(self.token_file, self.SCOPES)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                # refresh token
                creds.refresh(Request())
            else:
                # create the token by the first time, using the authorization flow
                if not self.client_secret:
                    raise Exception(f"{self.name}.init_service failed: trying to create a new token, and there is no a client secret")
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.client_secret,    # the client secret of the App
                    self.SCOPES
                )
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())

        try:
            service = build('drive', 'v3', credentials=creds)
            self.service = service    # service created!
        except Exception as e:
            raise Exception(f"{self.name}.init_service failed: {str(e)}")

    def list_all_files(self, query='', attr=''):
        """Based in the code from: https://developers.google.com/drive/api/v3/search-files
        Reference: https://developers.google.com/drive/api/v3/reference/files/list

        @param query             String. The query to search files for, e.g. "name='foo.txt'"
        @param fields (optional) List. A list of metadata attributes to be retrieved, e.g. ['name', 'size', 'mimeType']
        @return On success, a list of dictionaries describing each file found, as retrieved by the method service.files().list().
                If not found, retrieves [].
        """

        if not self.service or not query: return

        data = []
        page_token = None
        while True:
            if not attr or not (type(attr) is list):
                req_fields = 'nextPageToken, files(id, name, mimeType, parents)'
            else:
                req_fields = 'nextPageToken, files(' + ','.join(attr) + ')'

            #print("query:", query)
            response = self.service.files().list(
                q = query,
                pageSize = 20,       # The maximum number of files to return per page. Partial or empty result pages are possible 
                                     # even before the end of the files list has been reached. Acceptable values are 1 to 1000, inclusive. 
                                     # (Default: 100)
                spaces = 'drive',    # A comma-separated list of spaces to query within the corpus. Supported values are 'drive', 
                                     # 'appDataFolder' and 'photos'.
                fields = req_fields,
                pageToken = page_token
                ).execute()

            n_max = 20     # LIMIT to n_max items ............. QUIT LATER!!!
            for file in response.get('files', []):
                data.append(file)

                if n_max == 0: break
                n_max -= 1

            page_token = response.get('nextPageToken', None)
            if page_token is None:
                break

        return data

    def list_directory(self, path = '', attr=[], fileId=''):
        """List the content of a directory. The paths '/', and '' (empty) are allowed to refer
        to the root folder.
        @param path String. The path to scan for.
        @param fileId (optional) String. If given, this overwrites path.
        @param attr (optional) List. The attributes to be retrieved for the entries.
        @return A list of dicts, each containing basic attributes for the entry ('name', 'id',
                'mimeType','size','modifiedTime','parents')
        @raise Exception, if the path does not exist, or it is not a directory.
        """
        if not self.service:
            raise Exception(f"{self.name}.list_directory: API service not started")

        if not fileId:
            ROOT_ID = "root"
            if not path or path == '/':
                parentId = ROOT_ID
            else:
                parent = self.getFileId(path, attr=['mimeType'])
                if not parent:
                    raise Exception(f"{self.name}.list_directory: File not found: '{path}'")
                elif parent.get('mimeType','') != MIME_TYPE_FOLDER:
                    raise Exception(f"{self.name}.list_directory: It is not a directory: '{path}'")
                parentId = parent['id']
        else:
            parentId = fileId

        query = f"'{parentId}' in parents"
        if not attr:
            # basic metadata
            attr = attr=['name','id','mimeType', 'size', 'modifiedTime','parents']

        return self.list_all_files(query=query, attr=attr)

    def list_folders(self, name = '', parentId = ''):
        """List all folders with a specific name. To look sub-folders into a specific 
        parent folder, the paramenter parentID is the ID of such a parent.
        If no parent ID is given, it will list folders under the root location
        """

        if not self.service: return

        ROOT_ID = 'root'
        query = f"mimeType='{self.MIME_TYPE_FOLDER}'"
        if name: query += f" and name='{name}'"
        if parentId and parentId != '/':
            query += f" and '{parentId}' in parents"
        else:
            query += f" and '{ROOT_ID}' in parents"
        
        return self.list_all_files(query)

    def list_files(self, name = '', mimeType = '', parentId = ''):
        """List all files with a specific name into a specific location. 
        If not mimeType is given, will list all entries that are not folders.
        The parentId is the ID of the folder into which to look the files. 
        If no parent ID is given, it will list files under the root location.
        """
        if not self.service: return

        if not mimeType:
            query = f"mimeType!='{self.MIME_TYPE_FOLDER}'"
        else:
            query = f"mimeType='{mimeType}'"
        if name:
            # removing dealing '/'
            if name[0] == '/': name = name[1:]
            query += f" and name='{name}'"
        ROOT_ID = 'root'
        if parentId and parentId != '/':
            query += f" and '{parentId}' in parents"
        else:
            query += f" and '{ROOT_ID}' in parents"
        
        return self.list_all_files(query)

    def delete_files(self, name = '', mimeType = '', parentId = ''):
        """Delete all files with a specific name into a specific location.
        The parameters name, mimeType and parentId are like in the method
        list_files()
        """
        if not self.service: return

        files = self.list_files(name=name, mimeType=mimeType, parentId=parentId)
        if not files: return
        print(f"{len(files)} results found")
        for file in files:
            ans = input(f"delete \'{file['name']}\' [y]es/[n]o/[c]ancel? This action cannot be undone: ")
            if ans.upper() == 'Y':
                id = file['id']
                self.service.files().delete(fileId=id).execute()
            elif ans.upper() == 'C':
                break

    def delete_folders(self, name = '', parentId = ''):
        """Delete all folders with a specific name into a specific location.
        The parameters nameand parentId are like in the method
        list_files()
        """
        return self.delete_files(name=name, mimeType=MIME_TYPE_FOLDER, parentId=parentId)

    def remove(self, path = '', prompt = True, silent = False):
        """Remove a file, given its path. The file can be a normal file, or a directory.
        If it is a directory, the entire folder and all its content will be removed (be careful!)
        The method recognizes paths like /path/to/folder', or '/path/to/folder/foo.txt'

        @param path   String. The path to the file to be removed.
        @param silent Bool. If True, don't raise Exception if the file doesn't exist.
                      Implies prompt = False.
        @return None.
        @raise Exception, if the files does not exist.
        """

        if silent: prompt = False        # silent implies not prompt

        fileId = self.getFileId(path)
        if not fileId:
            if silent:
                return
            else:
                raise Exception(f"{self.name}.remove: File not found '{path}'")
        
        if prompt:
            ans = input(f"delete '{path}' [y]es/[n]o? This action cannot be undone: ")
            if ans.upper() == 'Y':
                self.service.files().delete(fileId=fileId).execute()
        else:
            self.service.files().delete(fileId=fileId).execute()

    def upload_file(self, origin = '', filename = '', originMimeType = '', destMimeType = '',
        dest = ''):
        """Upload a file from the local machine up to Drive.
        The file will have the new name <filename> if given, or else the same
        name as in origin.
        If <dest> is passed, the uploaded file will be moved to that folder. Otherwise,
        the file will remain in the root folder of Drive.

        @param origin String. The path of the file to be uploaded, e.g. 'path/to/file/foo.txt'
        @param originMimeType String. The MIME type of the uploaded file, e.g. 'text/csv'
        @param filename (optional) String. The name to be given to the new file into Drive.
        @param destMimeType (optonal) String. The MIME type to the uploaded file, e.g. MIME_TYPE_DOCUMENT, etc.
        @param dest (optional) String. The folder to move the uploaded the file in the destination.
        @return String. The uploaded file ID.
        """

        if not origin or not filename: return

        # cheching if the file exists
        if not os.path.exists(origin) or not os.path.isfile(origin):
            raise Exception(f"{self.name}.upload_file: File not found")
        # and is readable
        elif not (os.stat(origin).st_mode & stat.S_IRUSR):
            raise Exception(f"{self.name}.upload_file: File is not readable (check permissions)")

        file_metadata = {
            'name': filename,
        }
        if destMimeType: file_metadata['mimeType'] = destMimeType
        media = MediaFileUpload(
            origin,
            #mimetype='text/csv',
            mimetype=originMimeType,
            resumable=True)
        file = self.service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id').execute()

        fileId = file.get('id')
        if fileId and dest:
            folderId = self.getFileId(dest)
            if folderId:
                self.moveToFolderById(fileId, folderId)

        return fileId

    def searchFile(self, path = ''):
        """This is shorcut method to getFileId, with a predefined set of attributes
        @param path String. The path to search for.
        @return Metadata (dict) of the file, or {} if not found.
        """
        return self.getFileId(path, attr=['id', 'name', 'size', 'mimeType', 'modifiedTime', 'parents', 'md5Checksum'])
    
    def getFileId(self, path='', attr=[]):
        """Get the file ID from a Drive path, e.g.: dir1/dir2/file.txt.
        Normally, this method returns only the ID of the file. But if you set a list
        of attributes (e.g. attr = ['mimeType', 'size']), then those attributes (plus the ID)
        will be appended to the response and returned as in by the method get().

        NOTE: if the name contains '/', you must escape it with '\/' 
        e.g. 'file/a' -> 'file\/a'

        @param path String. The path of the Drive file to be located.
        @param attr (optional) List. A list of attributes to be retrieved if success.
        @return     If no attr is passed, returns the ID of the file on success, or an empty string 
                    on failure.
                    If attr is passed, return a dict of attributes on success, or {} on failure.
        """

        # remove dealing '/', e.g. '/path/to/my/folder'
        if path[0] == '/': path = path[1:]
        if not path: return

        # recognizing the escape character \/
        # bug 2021.08.1
        # as wildcard ('*') is not allowed in a file name, we will replace
        # temporarily the '\/' by '*', then split by '/' and newly 
        # replace back '*' by '/'
        if '*' in path:
            raise Exception(f"{self.name}.getFileId: path cannot contain wildcard characters ('*')")
        path = path.replace("\\/", '*')    # using "\\/" to avoid ambiguity

        folders = path.split('/')
        if folders[-1] == '':
            # if the path is ended with '/', e.g. 'path/to/my/folder/'
            folders = folders[:-1]
        if not folders: return
        parentId = "root"                 # start search in the root folder
        for folder in folders:            # descend through each folder in the path
            # converting '*' into '/'
            folder = folder.replace("*", "/")
            if not parentId: 
                # not found
                return '' if not attr else {}
            q = f"name='{folder}' and '{parentId}' in parents"
            
            # === debug ===
            #print(q)
            r = self.list_all_files(query=q, attr='id')
            
            # === debug ===
            #pprint(r)

            if r:
                # by the next iteration, take the current folder as the parent
                parentId = r[0].get('id', '')
            else:
                parentId = ''

        if not parentId:
            # not found
            return '' if not attr else {}

        # if not attr are given, return only the file ID. Otherwise, return
        # a dict of attributes (as retrived by the API method get())
        if not attr:
            return parentId
        else:
            fields = 'id'
            for a in attr:
                fields += f", {a}"
            r = self.service.files().get(fileId=parentId, fields=fields).execute()
            return r

    def getMimeTypeById(self, fileId = ''):
        """Get the MIME type of the file, given its ID

        @param fileId String. The file ID.
        @return String. The MIME type.
        """
        if not fileId: return None
        file = self.service.files().get(
            fileId=fileId,
            fields='mimeType'
            ).execute()
        if file:
            return file.get('mimeType')
        else:
            return None

    def getFileNameById(self, fileId = ''):
        """Get the file name, given its ID

        @param fileId String. The file ID.
        @return String. The file name.
        """
        if not fileId: return None
        file = self.service.files().get(
            fileId=fileId,
            fields='name'
            ).execute()
        if file:
            return file.get('name')
        else:
            return None

    def moveToFolderById(self, fileId = '', folderId = ''):
        """Move a file to a folder into Drive.
        https://developers.google.com/drive/api/v3/folder#python

        By using this in conjunction with getFileId, you can build sentences like
        -  API.moveToFolder(API.getFileId('foo.txt'), API.getFileId('path/to/move'))

        @param fileId   String. The ID of the file to be moved (see method getFileId()).
        @param folderId String. The ID of the folder to which move the file.
        @return None
        """
        if not fileId or not folderId: 
            # NOTE: .... maybe raise an Exception instead ?
            return

        drive_service = self.service
        # verifying the destination in a folder
        folder = drive_service.files().get(
            fileId=folderId,
            fields='mimeType'
            ).execute()
        if folder.get('mimeType') != MIME_TYPE_FOLDER:
            raise Exception(f"{self.name}.moveToFolderById: Destination is not a MIME type folder")

        # Retrieve the existing parents to remove
        file = drive_service.files().get(
            fileId=fileId,
            fields='parents'
            ).execute()
        previous_parents = ",".join(file.get('parents'))
        # Move the file to the new folder
        file = drive_service.files().update(
            fileId=fileId,
            addParents=folderId,
            removeParents=previous_parents,
            fields='id, parents'
            ).execute()

    def moveToFolder(self, filename='', foldername=''):
        """Move a file to a folder, but using paths instead of ID's.
        E.g.: moveToFolder('foo.txt', 'path/to/move')

        @param filename   String. The name of the file to be moved.
        @param foldername String. The name of the folder to which move the file.
        @return None
        """
        if not filename or not foldername: return
        fileId   = self.getFileId(filename)
        folderId = self.getFileId(foldername)
        if not fileId or not folderId: return        # not found
        self.moveToFolderById(fileId, folderId)

    def copyToFolderById(self, fileId = '', folderId = ''):
        """Make a copy of a file, into another folder.
        https://stackoverflow.com/questions/64347544/how-to-rename-a-google-spreadsheet-via-google-drive-api-in-python

        By using this in conjunction with getFileId, you can build sentences like
        -  API.copyToFolder(API.getFileId('foo.txt'), API.getFileId('path/to/move'))

        @param fileId   String. The ID of the file to be copied (see method getFileId()).
        @param folderId String. The ID of the folder to which copy the file.
        @return None
        """
        if not fileId or not folderId: return

        copyId = self.service.files().copy(fileId=fileId).execute()["id"]
        self.moveToFolder(copyId, folderId)

    def copyToFolder(self, filename='', foldername=''):
        """Make a copy of a file into a folder, but using paths instead of ID's.
        e.g.: copyToFolder('foo.txt', 'path/to/move')

        @param filename   String. The name of the file to be copied (see method getFileId()).
        @param foldername String. The name of the folder to which copy the file.
        @return None
        """
        if not filename or not foldername: return
        fileId   = getFileId(filename)
        folderId = getFileId(foldername)
        if not fileId or not folderId: return        # not found
        self.moveToFolderById(fileId, folderId)

    def rename(self, oldFilename='', newFilename=''):
        """Rename a file. The file keeps holding in the same folder/parent.
        To move the file no another folder, plus changing the filename, use first
        the method moveToFolder(), then rename().

        e.g.: rename('path/to/file/foo.txt', 'foo2.txt')
        the result is the file 'path/to/file/foo2.txt'

        @param oldFilename String. The file to be renamed.
        @param newFilename String. The new name (in the same folder/parent where it was)
        @return None
        @raises Exception, if the file named oldFilename does not exist.
        """
        if not oldFilename or not newFilename: return

        fileId = getFileId(oldFilename)
        if not fileId:
            # not found
            raise Exception(f"{self.name}.rename: File not found")
        body = {"name": newFilename}
        self.service.files().update(fileId=fileId, body=body).execute()

    def _parse_dest_path(self, path = ''):
        """This is an auxiliary function that helps to parse a path as a folderId, plus
        optionally a filename.
        Examples:

        a) path/to/folder    will be parsed as a folderId (if that folder actually exists)
        b) path/to/folder/   is the same than before
        c) path/to/folder/foo.txt  will be parsed as a folderId and a filename

        NOTE: in all cases, a leading '/' will be ignored, '/path/to/folder' is the same
        that 'path/to/folder'

        @param path String. The destination path to be parsed.
        @return If the folder doesn't exist, returns None. Otherwise, it can return
                either a tuple (folderId,filename), or (folderId, ''), depending of wheter
                a filename is given or not in the path (cases (b) or (c))
        """
        sep = '/'
        if path and path[0] == sep:
            # remove dealing '/'
            path = path[1:]
        if not path: return None
        v = path.split(sep)
        folderId = "root"
        mimeType = MIME_TYPE_FOLDER
        i = 0
        # iterates through of the path (array v)
        while i < len(v) and mimeType == MIME_TYPE_FOLDER:
            filename = v[i]
            subfolders = self.list_folders(name = filename, parentId = folderId)
            if subfolders:
                folderId = subfolders[0]['id']
            else:
                if i == len(v) - 1:
                    # e.g. 'path/to/folder/foo.txt', then folderId = ID_OF('path/to/folder/'), 
                    # and filename = 'foo.txt'
                    return (folderId, filename)
                else:
                    # path not found
                    return None
            i += 1
        # this is the case 'path/to/folder/', no filename given
        return (folderId, '')

    def createFolder(self, path = ''):
        """Create a new folder in Drive. It recognizes string names like
        '/path/to/my/new/folder', or '/path/to/my/new/folder/'
        @param path String. The path to the folder to be created.
        @return On success, return the ID of the new created folder.
        """
        ROOT_ID = "root"
        return self.createFolderRecursively(path, ROOT_ID)

    def createFolderRecursively(self, path = '', parentId = ''):
        """Auxiliary function to createFolder()
        """
        if not parentId: return ''

        # remove dealing and trailing '/'
        if path:
            if path[0] == '/': path = path[1:]
            if path[-1] == '/': path = path[:-1]
        if not path: 
            raise Exception(f"{self.name}.createFolder: Incorrect path: '{path}'")
        
        v = path.split('/', 1)
        a = v[0]
        if len(v) > 1:
            b = v[1]
        else:
            b = None

        # --- debug ---
        # is 'a' child of parentId ?
        #print(f"create recursively:  a='{a}', b='{b}'")
        #
        q = f"name='{a}' and '{parentId}' in parents"
        # --- debug ---
        #print(f"query: {q}")

        r = self.list_all_files(query=q, attr='id')
        if not r:

            # --- debug ---
            #print(f"....create '{a}' as a child of {parentId}")
            #
            file_metadata = {
                'name': a,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            file = self.service.files().create(body=file_metadata,
                fields='id').execute()

            # Move the created folder to the new location
            fileId = file.get('id')
            # Retrieve the existing parents to remove
            file = self.service.files().get(
                fileId=fileId,
                fields='parents'
                ).execute()
            previous_parents = ",".join(file.get('parents'))
            file = self.service.files().update(
                fileId=fileId,
                addParents=parentId,
                removeParents=previous_parents,
                fields='id, parents'
                ).execute()
            parentId = file.get('id')
        else:
            parentId = r[0]['id']

        # now, parentId is the id of 'a'
        # then, call recursively searching for the child 'b' of 'a'
        if b:
            return self.createFolderRecursively(b, parentId)
        else:
            return parentId

    def sync(self, local_path='', remote_path='', regex = '',
        recursion_level = 1, max_recursion_level = 10):
        """Synchronize local and remote path. Traverses recursively the local directory (*),
        recreates the directory structure in the remote path, and copies only the files
        more recently modified, or with a larger size.

        (*)NOTE: if the local_path corresponds to regular file (instead of a directory) it will
        synchronize that single file to the remote path.

        @param local_path String. The full path of the source folder.
        @param remote_path String. The path of the remote folder.
        @param regex (optional) String. Only sync the local files matching regex.
                     e.g. regex = '.*\.txt$' will match 'foo.txt', but not 'foo.csv'
        @param max_recursion_level Int. Max recursion level to look into it. Default 10.
        @return None.
        @raise Exception, if the local path cannot be properly read (e.g., permissions), 
               or an exceptions arises on calling other methods of the API (like upload_file())
        """

        if not local_path or not remote_path: return

        if recursion_level > max_recursion_level: return

        # NOTE.- 2021.08.24
        # CAUTION: Removing trailing / to all paths.
        # As the program doesn't distinguish between folder/foo and folder/foo/, and
        # keeping this trailing can bring to folder/foo//folder2 while concatenation
        # with '/' (!!!)
        if local_path[-1] == '/': local_path = local_path[:-1]
        if remote_path[-1] == '/': remote_path = remote_path[:-1]
        print(F"Syncing [Local]:{local_path} to [Drive]:{remote_path}")

        if not os.path.exists(local_path):
            raise Exception(f"{self.name}.sync: Local path not found")
        
        # try creating the remote folder (is not exist), otherwise
        # list its content
        r = self.searchFile(remote_path)
        if not r or r.get('mimeType') != MIME_TYPE_FOLDER:
            # NOTE: if the file exists but it is a regular file, then it will create a
            #       folder with the same name. This is weird, but Google Drive allows
            #       to have several files with the same name.
            #       By future versions, this behavior could be changed to delete the
            #       older (regular) file.
            print(f"+ creating folder '{remote_path}'")
            remoteFolderId = self.createFolder(remote_path)
        else:
            remoteFolderId = r['id']

        if os.path.isfile(local_path):
            # if the source is a file
            self._sync_file(local_path, remote_path)
            return
        elif not os.path.isdir(local_path):
            # is it is not a file, neither a directory: fail
            raise Exception(f"{self.name}.sync: Local path is not a directory")

        # otherwise, the source is a directory ...
        # list the content of the local directory
        local_files = os.listdir(local_path)

        # list the content of the remote directory
        remote_files = self.list_directory(fileId = remoteFolderId)

        # regex matcher
        if regex:
            matcher = re.compile(regex)
        else:
            matcher = None

        for entry in local_files:

            local_file = local_path + '/' + entry
            if os.path.isdir(local_path + '/' + entry):
                self.sync(local_path + '/' + entry, remote_path + '/' + entry, 
                    regex= regex,
                    recursion_level = recursion_level + 1, 
                    max_recursion_level = max_recursion_level)
            elif os.path.isfile(local_path + '/' + entry):
                # upload this file
                #print(f"match [{regex}]? {not not matcher.match(local_file)}")
                if matcher and not matcher.match(local_file):
                    # if regex is given, omit the files not matching the pattern
                    continue
                
                print(f"CALL _sync_file({local_file}, {remote_path})")
                self._sync_file(local_file, remote_path)

    def _sync_file(self, local_file, dest):
        """Auxiliary function to sync a single file (not a folder).
        If the file does not exist in the destination, it will be created.
        If a file with that name actually exists, then it will update based in
        a criteria: 
          - if the sizes between local and remote are different, or
          - if the modification time is newer in the local file

        @param local_file String. The full path of the source file.
        @param dest       String. The path of the destination folder.
        @ return          None
        """
        if not local_file or not dest: return

        # inspect the destination
        filename    = os.path.basename(local_file)
        remote_name = dest + '/' + filename
        r = self.searchFile(remote_name)
        if not r:
            print(f">> uploading '{local_file}' to '{remote_name}")
            self.upload_file(origin = local_file, filename = filename, 
                dest = dest)
        else:

            # file exists, check timestamp and size
            _fstat = os.stat(local_file)

            """ NOTE: how to convert from localtime to utctime
            https://stackoverflow.com/questions/79797/how-to-convert-local-time-string-to-utc

            Option 1 .
            >>> import datetime
            >>> utc_datetime = datetime.datetime.utcnow()
            >>> utc_datetime.strftime("%Y-%m-%d %H:%M:%S")
            '2010-02-01 06:59:19

            Option 2.
            NOTE - If any of your data is in a region that uses DST, use pytz and take a look at John Millikin's answer.

            If you want to obtain the UTC time from a given string and your lucky enough to be in a region in the world that either doesn't use DST, or you have data that is only offset from UTC without DST applied:

            --> using local time as the basis for the offset value:

            >>> # Obtain the UTC Offset for the current system:
            >>> UTC_OFFSET_TIMEDELTA = datetime.datetime.utcnow() - datetime.datetime.now()
            >>> local_datetime = datetime.datetime.strptime("2008-09-17 14:04:00", "%Y-%m-%d %H:%M:%S")
            >>> result_utc_datetime = local_datetime + UTC_OFFSET_TIMEDELTA
            >>> result_utc_datetime.strftime("%Y-%m-%d %H:%M:%S")
            '2008-09-17 04:04:00'

            >>> UTC_OFFSET = 10
            >>> result_utc_datetime = local_datetime - datetime.timedelta(hours=UTC_OFFSET)
            >>> result_utc_datetime.strftime("%Y-%m-%d %H:%M:%S")
            '2008-09-17 04:04:00'

            Option 3.
            >>> import datetime

            >>> timezone_aware_dt = datetime.datetime.now(datetime.timezone.utc)
            """

            remote_mtime = datetime.strptime(r['modifiedTime'], "%Y-%m-%dT%H:%M:%S.%fZ").timestamp()
            UTC_OFFSET_TIMEDELTA = datetime.utcnow() - datetime.now()
            # NOTE: local mtime in UTC (!)
            local_mtime  = (datetime.fromtimestamp(_fstat.st_mtime) + UTC_OFFSET_TIMEDELTA).timestamp()
            
            remote_size  = r['size']
            local_size   = _fstat.st_size
            if local_size != int(remote_size) or local_mtime > remote_mtime:
                print(f"size: [local]{local_size} [remote]{remote_size}")
                print(f"mtime: [local]{datetime.fromtimestamp(local_mtime)} [remote]{datetime.fromtimestamp(remote_mtime)}")
                print(f">> updating '{local_file}'")
                self.remove(path = remote_name, prompt = False)
                self.upload_file(origin = local_file, filename = os.path.basename(local_file), 
                    dest = dest)

    def __del__(self):
        pass
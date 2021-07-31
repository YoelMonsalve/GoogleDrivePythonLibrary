# GoogleDrivePythonLibrary
This library allows you to easily interact with Drive, as it was a common file system. Create folders, upload files, remove files, list directories and more. Also, it understands string paths, like 'path/to/folder/foo.txt'

# References
* [https://developers.google.com/drive/api/v3/quickstart/python](https://developers.google.com/drive/api/v3/quickstart/python)
* [https://developers.google.com/drive/api/v3/reference/](https://developers.google.com/drive/api/v3/reference/)

# Methods
## Low level methods
* Init a service from your client_secret ([reference](https://developers.google.com/drive/api/v3/quickstart/python))
* List all files (folders are also considered files) matching a query ([reference](https://developers.google.com/drive/api/v3/reference/files/list))
* List all entries under a directory, understanding a string path syntax (e.g. 'path/to/folder/')
* List folders under a parent ID
* List all files under a parent ID
* Delete all folders with a given name and parentID
* Delete all files with a given name and parentID
* getFileNameById: get a file name from its ID.
* getMimeTypeById: get a file MIME type from its ID.

## High level methods
* `getFileId`: get a file ID from string path.
* `serchFile`: return the basic attributes of a file (id, name, size, mimeType, modifiedTime, parents) from a string path.
* `copyToFolder`: copy a file to another folder. This understands string paths.
* `moveToFolder`: move a file to another folder. This understands string paths.
* `rename`: rename a file
* `createFolder`: create a folder under the root location of Drive. Understands string paths, and you can created nested folder in a way: e.g. `createFolder('/my/new/folder')` will create a new folder root->my->new->folder
* `uploadFile`: upload a file to an existing remote folder, allowing you to specify a different name. Example, `upload_file('foo.txt','foo2.txt', dest='my/folder')` will create the new file `my/folder/foo2.txt` with the content of `foo.txt`
* `sync`: automatically synchronize a local folder with a remote drive folder. I will traverse recursively the local folder, recreating the folders structure in the remote, and uploading/updating files if size is different or modification time is newer in local.


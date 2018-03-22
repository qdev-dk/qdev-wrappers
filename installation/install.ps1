# This script installs all you need to use qcodes:
# - Miniconda (Python), including spyder and jupyter
# - Git (version control)
# - Qcodes, qdev-wrappers, broadbean
# - creates links on desktop and quick access
# To make sure everything works as expected go to "Start->Add or remove programs"
# and search for "Python" to remove any previous installation of Anaconda,
# Miniconda or similiar. Beware that this removes all your python environments
# and if you have made changes to any distribution (which you should never do)
# you will lose these changes. To see if you have made changes you can either
# call "git status" in the corresponding repository directory from the git bassh
# or install the github gui.
# For a clean reinstallation also remove previous installs of git.
# To run this installation script, right-click it and select run with PowerShell



# Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
$miniconda_url = "https://repo.continuum.io/miniconda/Miniconda3-latest-Windows-x86_64.exe"
$miniconda_exe = "$env:TEMP\miniconda.exe"
$env_bat = "$env:TEMP\create_qcodes_env.bat"
$miniconda_install_path = "$HOME\miniconda\"
$git_exe = "$env:TEMP\git.exe"
$git_url= 'https://git-scm.com/download/win'

$qcodes_url = "https://github.com/QCoDeS/Qcodes.git"
$qdev_wrappers_url = "https://github.com/qdev-dk/qdev-wrappers"
$broadbean_url = "https://github.com/QCoDeS/broadbean"


# install miniconda and update
Write-Host 'downloading miniconda, please wait'
(New-Object System.Net.WebClient).DownloadFile($miniconda_url, $miniconda_exe)| Out-Host
Write-Host 'installing miniconda'
&$miniconda_exe /InstallationType=JustMe /AddToPath=1 /S "/D=$miniconda_install_path" | Out-Host
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User") 
Write-Host 'updating miniconda'
conda update -y conda
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

# download git
Write-Host 'download latest version of git'
$html = Invoke-WebRequest -Uri $git_url
$e = ($html.ParsedHtml.getElementsByTagName(‘a’) | Where{ $_.innerText -eq ‘64-bit Git for Windows Setup’ } )
$git_setup_url = $e.attributes.getNamedItem('href').nodeValue()
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
Invoke-WebRequest -Uri $git_setup_url -OutFile $git_exe

# install git
Write-Host 'installing git'
&$git_exe "/SILENT"| Out-Host
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
cd $Home

# clone repos
Write-Host 'cloning qcodes relvant repos'
git clone $qcodes_url
git clone $qdev_wrappers_url
git clone $broadbean_url

# create qcodes virtualenv
Write-Host 'creating the virtual environment'
conda env create -f "$Home\Qcodes\environment.yml"
Write-Host 'activating the virtual environment'
activate qcodes

Write-Host 'installing spyder'
conda install -y spyder

Write-Host 'installing jupyter'
conda install -y jupyter

Write-Host 'installing qcodes'
$env_cmd = 'CALL activate qcodes
CAll pip install -e %UserProfile%\Qcodes
CALL pip install -e %UserProfile%\qdev-wrappers
CALL pip install -e %UserProfile%\broadbean'
$env_cmd | Set-Content $env_bat
cmd /c $env_bat
# &$env_bat | Out-Host



# make desktop shortcuts
Write-Host 'creating desktop shortcuts'
Copy-Item -Path "$Home\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Anaconda3 (64-bit)\Spyder (qcodes).lnk" -Destination "$Home\Desktop\"
Copy-Item -Path "$Home\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Anaconda3 (64-bit)\Jupyter Notebook (qcodes).lnk" -Destination "$Home\Desktop\"
Copy-Item -Path "$Home\qdev-wrappers\qdev_wrappers\templates\monitor.cmd" -Destination "$Home\Desktop\"

# add to quick access bar
Write-Host 'adding repos to quick access bar'
$o = new-object -com shell.application
$o.Namespace("$Home\Qcodes").Self.InvokeVerb("pintohome")
$o.Namespace("$Home\qdev-wrappers").Self.InvokeVerb("pintohome")
$o.Namespace("$Home\broadbean").Self.InvokeVerb("pintohome")


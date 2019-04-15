# This installation script installs most of the necessary components to run qcodes
# in a setup as it is widely used at Qdev.
# It will install the following components:
# - Miniconda (Python), including spyder and jupyter
# - Git (version control)
# - Code repositories: Qcodes, qdev-wrappers, broadbean
# - create links on desktop and quick access
# You will need to manually install NI-VISA, because to do so a (free) user account 
# with NI is required. You can download it from:
# http://www.ni.com/da-dk/support/downloads/drivers/download.ni-visa.html
# (if the link is broken, google for `NI VISA download`
# 
# To make sure everything works as expected, before you start the installation
# remove any previous installed versions of python.
# For that go to "Start->Add or remove programs"
# and search for "Python" and remove any relevant entries like Anaconda,
# Miniconda or similiar. Beware that this removes all your python environments
# and if you have made changes to any distribution (which you should never do)
# you will lose these changes. To see if you have made changes you can either
# call "git status" in the corresponding repository directory from the git bassh
# or install the github gui.
# For a clean reinstallation also remove previous installs of git.

# To download this installation script, you can copy and paste it directly from github,
# clone it, or download it by going to the root of this repository on github and clicking
# the green button and select `download as zip`. 
# When you have this file `install.ps1` on disk you can outcomment the repository
# locations in the first lines of the script if you don't want to install some
# of the repositories.
# To run the script right-click it and select run with PowerShell.
# On some systems this does not work. In this case start `Windows power shell ISE` from the 
# start menu and execute there:
# `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Unrestricted`
# to temporarily elevate the rights to executed foreign scripts
# then open or paste the script and press run (or press F5).

# When the installation is complete you can run jupyter (qcodes) from the desktop or
# start menu. Navigate to %USER%/qcodes/docs/examples to find example notebooks 
# to get started with qcodes. A good starting point is `DataSet/Dataset Context Manager.ipynb`



$chickpea_url = "https://github.com/nataliejpg/chickpea"
$qcodes_url = "https://github.com/QCoDeS/Qcodes.git"
$qdev_wrappers_url = "https://github.com/qdev-dk/qdev-wrappers"
$broadbean_url = "https://github.com/QCoDeS/broadbean"


# Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
$miniconda_url = "https://repo.continuum.io/miniconda/Miniconda3-latest-Windows-x86_64.exe"
$miniconda_exe = "$env:TEMP\miniconda.exe"
$env_bat = "$env:TEMP\create_qcodes_env.bat"
$conda_install_bat = "$env:TEMP\conda_install.bat"
$miniconda_install_path = "$HOME\miniconda\"
$git_exe = "$env:TEMP\git.exe"
$git_url= 'https://git-scm.com/download/win'



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
$e = ($html.ParsedHtml.getElementsByTagName('a') | Where{ $_.innerText -eq '64-bit Git for Windows Setup' } )
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
if($qdev_wrappers_url){
    git clone $qdev_wrappers_url
}
if($broadbean_url){
    git clone $broadbean_url
}
if($chickpea_url){
    git clone $chickpea_url
}

# create qcodes virtualenv
Write-Host 'creating the virtual environment'
conda env create -f "$Home\Qcodes\environment.yml"
Write-Host 'activating the virtual environment and installing spyder+jupyter'

$install_cmd = 'CALL activate qcodes
CALL conda install -y spyder
CALL conda install -y jupyter
CALL conda install -y scipy'
$install_cmd | Set-Content $conda_install_bat
cmd /c $conda_install_bat

Write-Host 'installing qcodes'
$env_cmd = 'CALL activate qcodes
CAll pip install -e %UserProfile%\Qcodes'
$new_line = "`r`n"
if($qdev_wrappers_url){
    $env_cmd += $new_line + 'CALL pip install -e %UserProfile%\qdev-wrappers'
}
if($broadbean_url){
    $env_cmd += $new_line + 'CALL pip install -e %UserProfile%\broadbean'
}
if($chickpea_url){
    $env_cmd += $new_line + 'CALL pip install -e %UserProfile%\chickpea'
}
$env_cmd | Set-Content $env_bat
cmd /c $env_bat
# &$env_bat | Out-Host



# make desktop shortcuts
Write-Host 'creating desktop shortcuts'
Copy-Item -Path "$Home\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Anaconda3 (64-bit)\Spyder (qcodes).lnk" -Destination "$Home\Desktop\"
Copy-Item -Path "$Home\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Anaconda3 (64-bit)\Jupyter Notebook (qcodes).lnk" -Destination "$Home\Desktop\"
if($qdev_wrappers_url){
    Copy-Item -Path "$Home\qdev-wrappers\qdev_wrappers\templates\monitor.cmd" -Destination "$Home\Desktop\"
}

# add to quick access bar
Write-Host 'adding repos to quick access bar'
$o = new-object -com shell.application
$o.Namespace("$Home\Qcodes").Self.InvokeVerb("pintohome")
if($qdev_wrappers_url){
    $o.Namespace("$Home\qdev-wrappers").Self.InvokeVerb("pintohome")
}
if($broadbean_url){
    $o.Namespace("$Home\broadbean").Self.InvokeVerb("pintohome")
}


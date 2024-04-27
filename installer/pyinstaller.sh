echo "##########################"
echo "Running PyInstaller script"
echo "##########################"

echo "Current path $(pwd)"

if [ "${PWD##*/}" == "installer" ]
then
  prefix="."
  scriptprefix=".."
  versionprefix="."
else
  prefix="./installer"
  scriptprefix="."
  versionprefix=".."
fi

echo "\n"
echo "\n"

echo "##########################"
echo "Setting paths"
echo "##########################"

workdir="$prefix/build"
echo "workdir:" $workdir
distdir="$prefix/dist"
echo "distdir:" $distdir
specpath="$prefix/spec"
echo "spec path:" $specpath
versionfile="$versionprefix/version.rc"
echo "version file:" $versionfile
scriptpath="$scriptprefix/explorer_ui.py"
echo "script path:" $scriptpath

echo "\n"
echo "\n"

echo "##########################"
echo "Deleting old builds"
echo "##########################"

echo "Deleting build $workdir"
rm -rf $workdir
echo "Deleted"

echo "Deleting dist $distdir"
rm -rf $distdir
echo "Deleted"

echo "Deleting spec $specpath"
rm -rf $specpath
echo "Deleted"

echo "##########################"
echo "Building  UI"
echo "##########################"

echo "Running pyinstaller -F --collect-submodules=pydicom $scriptpath --distpath $distdir --workpath $workdir --version-file $versionfile"

pyinstaller -F --collect-submodules=pydicom $scriptpath --specpath $specpath --distpath $distdir --workpath $workdir --version-file $versionfile

echo "##########################"
echo "Done"
echo "##########################"

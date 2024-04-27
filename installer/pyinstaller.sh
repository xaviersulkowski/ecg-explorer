if [ "${PWD##*/}" == "installer" ]
then
  prefix="."
else
  prefix="./installer"
fi

specpath="$prefix/explorer_ui.spec"
echo "specpath:" $specpath
workdir="$prefix/build"
echo "workdir:" $workdir
distdir="$prefix/dist"
echo "distdir:" $distdir


pyinstaller $specpath --distpath $distdir --workpath $workdir

#!/bin/bash

make_module() {
  MODULE_NAME=$1

  echo "#define MODULE_EXPORT" > $MODULE_NAME.cppm
  echo "" >> $MODULE_NAME.cppm
  echo "export module FULL_NAME_${MODULE_NAME};" >> $MODULE_NAME.cppm

  shift 1

  while [ $# -ne 0 ];
  do
    echo '#include "'$1'"' >> $MODULE_NAME.cppm
    shift 1
  done
}


for file in *;
do
  if [[ "$file" =~ \.c$ || "$file" =~ \.cpp$ ]]
  then
    # For each source files, create a module along with the header, if found.

    if [ -f $(echo ${file} | sed 's/\.c/\.h/') ]
    then
      make_module $(echo ${file} | sed 's/\.c//') \
        $(echo ${file} | sed 's/\.c/\.h/') \
        ${file}
    else
      # Create a module just for the implementation file if no header was
      # found.
      make_module $(echo ${file} | sed 's/\.c//') \
        ${file}
    fi
  elif [[ "$file" =~ \.h$ || "$file" =~ \.hpp$ ]]
  then
    # For each header, create a module from only the header if there is no
    # source file previously handled for it.

    if [ ! -f $(echo ${file} | sed 's/\.h/\.c/') ]
    then
      make_module $(echo ${file} | sed 's/\.h//') \
        ${file}
    fi
  fi
done


#!/bin/bash

make_module() {
  echo $@
  MODULE_NAME=$(echo "$1" | sed 's/\.(c\|cpp\|cxx\|cc)$//g' | sed 's/\.//g' | sed 's@\./@@g' | sed 's@/@_@g')
  MODULE_FILE="$1cppm"
  shift 1

  echo "#define MODULE_EXPORT" > $MODULE_FILE
  echo "" >> $MODULE_FILE
  echo "export module FULL_NAME_${MODULE_NAME};" >> $MODULE_FILE

  while [ $# -ne 0 ];
  do
    echo '#include "'$1'"' >> $MODULE_FILE
    shift 1
  done
}


for file in $(find . -type f);
do
  if [[ "$file" =~ \.c$ || "$file" =~ \.cpp$ || "$file" =~ \.cxx$ || "$file" =~ \.cc$ ]]
  then
    # For each source files, create a module along with the header, if found.
    if [ -f $(echo ${file} | sed -E 's/\.c(pp\|xx\|c)?/\.h\1/') ]
    then
      make_module $(echo ${file} | sed 's/\.(c\|cpp\|cxx\|cc)//') \
        $(echo ${file} | sed -E 's/\.c(pp\|xx\|c)?/\.h\1/') \
        ${file}
    else
      # Create a module just for the implementation file if no header was
      # found.
      make_module $(echo ${file} | sed 's/\.(c\|cpp\|cxx\|cc)//') \
        ${file}
    fi
  elif [[ "$file" =~ \.h$ || "$file" =~ \.hpp$ || "$file" =~ \.hxx$ || "$file" =~ \.hh$ ]]
  then
    if [[ -f $(echo ${file} | sed 's/h.*$/cppm/g') ]]
    then
      # If a module has been created for the source file associated with this
      # header, do not overwrite it...
      continue
    fi

    # For each header, create a module from only the header if there is no
    # source file previously handled for it.

    if [ ! -f $(echo ${file} | sed 's/\.(h\|hpp\|hxx\|hh)/\.c/') ]
    then
      make_module $(echo ${file} | sed 's/\.(h\|hpp\|hxx\|hh)//') \
        ${file}
    elif [ ! -f $(echo ${file} | sed 's/\.(h\|hpp\|hxx\|hh)/\.cpp/') ]
    then
      make_module $(echo ${file} | sed 's/\.(h\|hpp\|hxx\|hh)//') \
        ${file}
    elif [ ! -f $(echo ${file} | sed 's/\.(h\|hpp\|hxx\|hh)/\.cxx/') ]
    then
      make_module $(echo ${file} | sed 's/\.(h\|hpp\|hxx\|hh)//') \
        ${file}
    elif [ ! -f $(echo ${file} | sed 's/\.(h\|hpp\|hxx\|hh)/\.cc/') ]
    then
      make_module $(echo ${file} | sed 's/\.(h\|hpp\|hxx\|hh)//') \
        ${file}
    fi
  fi
done


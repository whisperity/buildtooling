import collections
import os
import operator


def rotate_list_of_cycles(lst):
  """
  Helper function that rotates :param lst: which should be a list containing
  inner lists that represent some cycles named by strings.
  The rotation is done IN PLACE, and each subcycle of :param lst: is rotated
  so that the alphanumerically first element is in the 0th position, but
  the ordering of elements cyclically related to each other is kept.

  >>> mylist = [["SystemPath", "SystemFail"], ["SomeItem", "SomeBullet"]]
  >>> rotate_list_of_cycles(mylist)
  >>> mylist
  [['SystemFail', 'SystemPath'], ['SomeBullet', 'SomeItem']]

  >>> mylist = [["Foo", "Baz", "Bar"], ["Foo", "Asd"]]
  >>> rotate_list_of_cycles(mylist)
  >>> mylist
  [['Bar', 'Foo', 'Baz'], ['Asd', 'Foo']]

  >>> mylist = [["BOne", "BTwo", "AOne"], \
                ["BOne", "AOne"],         \
                ["ZLast", "XSystem", "NFoobar"]]
  >>> rotate_list_of_cycles(mylist)
  >>> mylist
  [['AOne', 'BOne', 'BTwo'], ['AOne', 'BOne'], ['NFoobar', 'ZLast', 'XSystem']]

  >>> mylist = [['D', 'C', 'B', 'A']]
  >>> rotate_list_of_cycles(mylist)
  >>> mylist
  [['A', 'D', 'C', 'B']]
  """

  for i, c in enumerate(lst):
    common_prefix = os.path.commonprefix(c)
    sort_based_on_char_idx = len(common_prefix)

    # Expand the strings in the list so the sort character index is always
    # in range. (' ' < any alphanumerical letter)
    expand = list(map(lambda s: s.ljust(sort_based_on_char_idx + 1), c))

    # We must not just sort the list because this list represents an ordered
    # cycle in the graph! Instead, rotate that the "smallest" key is the
    # first.
    min_idx, _ = min(enumerate(expand), key=operator.itemgetter(1))
    d = collections.deque(expand)
    d.rotate(-min_idx)

    lst[i] = list(map(lambda s: s.rstrip(), d))

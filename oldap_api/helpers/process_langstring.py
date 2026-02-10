from enum import Enum
from typing import Callable

from oldaplib.src.enums.attributeclass import AttributeClass
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.oldaperror import OldapErrorValue
from oldaplib.src.model import Model
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_qname import Xsd_QName
from oldaplib.src.xsd.xsd_string import Xsd_string

from oldap_api.views import known_languages


def process_langstring(obj: Model,
                       attr: AttributeClass,
                       newval: list | dict | None,
                       notifier: Callable[[Enum | Iri], None] = None):
    if newval != "NotSent":
        if isinstance(newval, list):
            if not newval:
                raise OldapErrorValue(f"Using an empty list is not allowed in the modify")
            if None in newval:
                raise OldapErrorValue(f"Using a None in a modify LangString is not allowed")
            obj[attr] = LangString(newval, notifier=notifier, notify_data=Xsd_QName(attr.value))
        elif isinstance(newval, dict):
            if not newval:
                raise OldapErrorValue(f"Using an empty dict is not allowed in the modify")
            if not set(newval.keys()).issubset({"add", "del"}):
                raise OldapErrorValue(f"The sent command (keyword in dict) is not known")
            if "del" in newval and "add" in newval:
                #
                # We have to check if we modified a Langstring (add and del both same language...)
                # If a langstring is being modified, the old value should be in newval["del"] and
                # the modified value should be in newval["add"]
                #

                #
                # first we prepend the '@' where necessary, since Xsd_string demands a '@' in the string!
                #
                newval["del"] = [x if x.startswith('@') else f'@{x}' for x in newval["del"]]

                dellangs = set([Xsd_string(x).lang for x in newval["del"]])
                addlangs = set([Xsd_string(x).lang for x in newval["add"]])
                mods = dellangs & addlangs
                if mods:
                    modified = [Xsd_string(x) for x in newval["add"] if Xsd_string(x).lang in mods]
                    for item in modified:
                        obj[attr][item.lang] = item.value
                    newval["del"] = [x for x in newval["del"] if Xsd_string(x).lang not in mods]
                    if not newval["del"]:
                        del newval["del"]
                    newval["add"] = [x for x in newval["add"] if Xsd_string(x).lang not in mods]
                    if not newval["add"]:
                        del newval["add"]
            if "del" in newval:
                deleting = newval["del"]
                if not isinstance(deleting, list):
                    raise OldapErrorValue("The given attributes in add and del must be in a list")
                if not deleting:
                    raise OldapErrorValue(f"Using an empty list is not allowed in the modify")
                #delstrs = [Xsd_string(x) for x in deleting]  # Convert to Xsd_strings
                for item in deleting:
                    try:
                        obj[attr].discard(item)
                    except KeyError as error:
                        raise OldapErrorValue(f"{item} is not a valid language. Supportet are {known_languages}")
            if "add" in newval:
                adding = newval["add"]
                if not isinstance(adding, list):
                    raise OldapErrorValue("The given attributes in add and del must be in a list")
                if not adding:
                    raise OldapErrorValue(f"Using an empty list is not allowed in the modify")
                if None in adding:
                    raise OldapErrorValue(f"Using a None in a modify LangString is not allowed")
                if not obj.get(attr):
                    obj[attr] = LangString(adding, notifier=notifier, notify_data=Xsd_QName(attr.value))
                else:
                    obj[attr].add(adding)
        elif newval is None:
            del obj[attr]
            if hasattr(obj, 'notify'):
                obj.notify()
        else:
            raise OldapErrorValue(f"Either a List or a dict is required.")

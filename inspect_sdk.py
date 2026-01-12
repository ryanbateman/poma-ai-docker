
import poma
from poma import Poma
import inspect

import poma.retrieval
import inspect
print("\nSignature for generate_cheatsheets:")
print(inspect.signature(poma.retrieval.generate_cheatsheets))
print(poma.retrieval.generate_cheatsheets.__doc__)

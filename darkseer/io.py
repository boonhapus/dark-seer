from typing import Union
import pathlib
import io


class Image(io.BytesIO):
    """
    TODO
    """
    def save_to_file(self, fp: [Union, str]):
        """
        TODO
        """
        if isinstance(fp, str):
            fp = pathlib.Path(str)

        with fp.open('wb') as img:
            img.write(self.getbuffer())

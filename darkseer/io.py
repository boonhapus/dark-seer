from typing import Union
import pathlib
import io


class Image(io.BytesIO):
    """
    TODO
    """
    def __init__(self, content: bytes, name: str, filetype: str):
        self.name = name
        self.filetype = filetype
        super().__init__(content)

    def save_to_file(self, fp: [Union, str]):
        """
        TODO
        """
        if isinstance(fp, str):
            fp = pathlib.Path(str)

        with fp.open('wb') as img:
            img.write(self.getbuffer())

    def __repr__(self):
        return f'<Image content=b"...", name={self.name}, filetype={self.filetype}>'

    def __str__(self):
        return f'<Image of {self.name}.{self.filetype}>'

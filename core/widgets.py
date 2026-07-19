from django import forms


class ISODateInput(forms.DateInput):
    """
    HTML5 <input type="date"> alanları tarayıcıda her zaman YYYY-MM-DD (ISO) formatı bekler.
    Django'nun varsayılan yerelleştirilmiş tarih biçimi (örn. tr için GG/AA/YYYY) bu alanlarda
    mevcut değerlerin veya initial değerlerin görünmesini engeller. Bu widget formatı sabitler.
    """
    input_type = "date"

    def __init__(self, attrs=None):
        attrs = {"type": "date", **(attrs or {})}
        super().__init__(attrs=attrs, format="%Y-%m-%d")

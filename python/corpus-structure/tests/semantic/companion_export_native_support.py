"""Shared controlled inputs and builders for companion export native support."""


def read_settings(native_settings, engine):
    from sqlalchemy.engine import make_url

    from corpus_structure.semantic.runtime import connection_settings

    database = engine.url.database
    writer = (
        make_url(native_settings.database.url)
        .set(database=database)
        .render_as_string(hide_password=False)
    )
    reader = (
        make_url(connection_settings(native_settings, "read").database.url)
        .set(database=database)
        .render_as_string(hide_password=False)
    )
    return native_settings.model_copy(
        update={
            "database": native_settings.database.model_copy(
                update={
                    "url": writer,
                    "reader_url": reader,
                }
            )
        }
    )

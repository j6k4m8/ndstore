{"name":"survey","models":{"Genre":{"name":"Genre","parent_class":"SQLObject","table_name":"","id_name":"","columns":{"name":{"type":"StringCol","column_name":"name","column_title":"","column_default":"","column_length":"200","column_size":"","column_precision":"","column_db_encoding":"","column_varchar":"","column_unique":"","column_not_none":"","column_alternate_id":""},"artists":{"type":"RelatedJoin","column_name":"artists","column_title":"","column_default":"","column_length":"","column_size":"","column_precision":"","column_db_encoding":"","column_varchar":"","column_unique":"","column_not_none":"","column_alternate_id":"","other_class_name":"Artist","other_method_name":"genres","original_other_class_name":"","original_other_method_name":"","join_type":"RelatedJoin"}},"relations":{}},"Artist":{"name":"Artist","parent_class":"SQLObject","table_name":"","id_name":"","columns":{"genres":{"type":"RelatedJoin","name":"genres","join_type":"RelatedJoin","other_class_name":"Genre","other_method_name":"artists"},"name":{"type":"StringCol","column_name":"name","column_title":"","column_default":"","column_length":"200","column_size":"","column_precision":"","column_db_encoding":"","column_varchar":"","column_unique":"","column_not_none":"","column_alternate_id":""},"albums":{"type":"MultipleJoin","column_name":"albums","column_title":"","column_default":"","column_length":"","column_size":"","column_precision":"","column_db_encoding":"","column_varchar":"","column_unique":"","column_not_none":"","column_alternate_id":"","other_class_name":"Album","other_method_name":"artist","original_other_class_name":"","original_other_method_name":"","join_type":"MultipleJoin"}},"relations":{},"ordered_columns":["name","genres","albums"]},"Album":{"name":"Album","parent_class":"SQLObject","table_name":"","id_name":"","columns":{"artist":{"type":"ForeignKey","name":"artist","join_type":"MultipleJoin","other_class_name":"Artist","other_method_name":"albums"},"name":{"type":"StringCol","column_name":"name","column_title":"","column_default":"","column_length":"200","column_size":"","column_precision":"","column_db_encoding":"","column_varchar":"","column_unique":"","column_not_none":"","column_alternate_id":""},"songs":{"type":"MultipleJoin","column_name":"songs","column_title":"","column_default":"","column_length":"","column_size":"","column_precision":"","column_db_encoding":"","column_varchar":"","column_unique":"","column_not_none":"","column_alternate_id":"","other_class_name":"Song","other_method_name":"album","original_other_class_name":"","original_other_method_name":"","join_type":"MultipleJoin"}},"relations":{},"ordered_columns":["name","artist","songs"]},"Song":{"name":"Song","parent_class":"SQLObject","table_name":"","id_name":"","columns":{"album":{"type":"ForeignKey","name":"album","join_type":"MultipleJoin","other_class_name":"Album","other_method_name":"songs"},"name":{"type":"StringCol","column_name":"name","column_title":"","column_default":"","column_length":"200","column_size":"","column_precision":"","column_db_encoding":"","column_varchar":"","column_unique":"","column_not_none":"","column_alternate_id":""}},"relations":{},"ordered_columns":["name","album"]}},"ordered_models":["Genre","Artist","Album","Song"]}
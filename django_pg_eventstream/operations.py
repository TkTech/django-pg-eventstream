from django.conf import settings
from django.db.migrations.operations.base import Operation


class CreateEventStreamTriggers(Operation):
    reversible = True

    def __init__(self, model_name, table_name, tracked_fields, pk_field):
        self.model_name = model_name
        self.table_name = table_name
        self.tracked_fields = tracked_fields
        self.pk_field = pk_field

    def state_forwards(self, app_label, state):
        # This operation doesn't modify the Django model state
        pass

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        event_table = getattr(settings, 'PG_EVENTSTREAM_TABLE', 'event_stream')
        tracked_fields_sql = ', '.join(
            f"'{field}'" for field in self.tracked_fields)

        schema_editor.execute(f"""
        CREATE OR REPLACE FUNCTION get_changed_fields(old_row anyelement, new_row anyelement, fields text[])
        RETURNS jsonb AS $$
        DECLARE
            result jsonb := '{{}}'::jsonb;
            field text;
        BEGIN
            FOREACH field IN ARRAY fields
            LOOP
                IF old_row IS NULL OR new_row IS NULL OR old_row.field IS DISTINCT FROM new_row.field THEN
                    result := result || jsonb_build_object(field, new_row.field);
                END IF;
            END LOOP;
            RETURN result;
        END;
        $$ LANGUAGE plpgsql;

        CREATE OR REPLACE FUNCTION process_event() RETURNS TRIGGER AS $$
        DECLARE
            tracked_fields text[];
            event_type integer;
            changes jsonb;
            model_name text;
            pk_field text;
            event_rows jsonb := '[]'::jsonb;
            old_row RECORD;
            new_row RECORD;
        BEGIN
            model_name := TG_TABLE_NAME;
            tracked_fields := TG_ARGV[0]::text[];
            pk_field := TG_ARGV[1]::text;

            IF (TG_OP = 'DELETE') THEN
                event_type := 3; -- Delete
                FOR old_row IN SELECT * FROM old_table LOOP
                    changes := get_changed_fields(old_row, NULL, tracked_fields);
                    EXECUTE format('SELECT $1.%I::text', pk_field) INTO pk_value USING old_row;
                    event_rows := event_rows || jsonb_build_object(
                        'event_type', event_type,
                        'model', model_name,
                        'object_pk', pk_value,
                        'changes', changes
                    );
                END LOOP;
            ELSIF (TG_OP = 'UPDATE') THEN
                event_type := 2; -- Update
                FOR old_row, new_row IN SELECT * FROM old_table, new_table LOOP
                    changes := get_changed_fields(old_row, new_row, tracked_fields);
                    IF changes != '{{}}'::jsonb THEN
                        EXECUTE format('SELECT $1.%I::text', pk_field) INTO pk_value USING new_row;
                        event_rows := event_rows || jsonb_build_object(
                            'event_type', event_type,
                            'model', model_name,
                            'object_pk', pk_value,
                            'changes', changes
                        );
                    END IF;
                END LOOP;
            ELSIF (TG_OP = 'INSERT') THEN
                event_type := 1; -- Create
                FOR new_row IN SELECT * FROM new_table LOOP
                    changes := get_changed_fields(NULL, new_row, tracked_fields);
                    EXECUTE format('SELECT $1.%I::text', pk_field) INTO pk_value USING new_row;
                    event_rows := event_rows || jsonb_build_object(
                        'event_type', event_type,
                        'model', model_name,
                        'object_pk', pk_value,
                        'changes', changes
                    );
                END LOOP;
            END IF;

            -- Bulk insert into the Event table
            IF jsonb_array_length(event_rows) > 0 THEN
                INSERT INTO {event_table} (timestamp, event_type, model, object_pk, payload)
                SELECT NOW(), (v->>'event_type')::int, v->>'model', v->>'object_pk', 
                       jsonb_build_object('changes', v->>'changes')
                FROM jsonb_array_elements(event_rows) as v;
            END IF;

            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;

        DROP TRIGGER IF EXISTS {self.table_name}_event_insert ON {self.table_name};
        DROP TRIGGER IF EXISTS {self.table_name}_event_update ON {self.table_name};
        DROP TRIGGER IF EXISTS {self.table_name}_event_delete ON {self.table_name};

        CREATE TRIGGER {self.table_name}_event_insert
        AFTER INSERT ON {self.table_name}
        REFERENCING NEW TABLE AS new_table
        FOR EACH STATEMENT EXECUTE FUNCTION process_event(ARRAY[{tracked_fields_sql}]::text[], '{self.pk_field}');

        CREATE TRIGGER {self.table_name}_event_update
        AFTER UPDATE ON {self.table_name}
        REFERENCING OLD TABLE AS old_table NEW TABLE AS new_table
        FOR EACH STATEMENT EXECUTE FUNCTION process_event(ARRAY[{tracked_fields_sql}]::text[], '{self.pk_field}');

        CREATE TRIGGER {self.table_name}_event_delete
        AFTER DELETE ON {self.table_name}
        REFERENCING OLD TABLE AS old_table
        FOR EACH STATEMENT EXECUTE FUNCTION process_event(ARRAY[{tracked_fields_sql}]::text[], '{self.pk_field}');
        """)

    def database_backwards(self, app_label, schema_editor, from_state,
                           to_state):
        schema_editor.execute(f"""
        DROP TRIGGER IF EXISTS {self.table_name}_event_insert ON {self.table_name};
        DROP TRIGGER IF EXISTS {self.table_name}_event_update ON {self.table_name};
        DROP TRIGGER IF EXISTS {self.table_name}_event_delete ON {self.table_name};
        """)

    def describe(self):
        return f"Create event stream triggers for {self.model_name}"
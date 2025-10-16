-- PostgreSQL trigger functions and triggers for maintaining event.assigned

CREATE OR REPLACE FUNCTION fn_event_volunteer_before_insert()
RETURNS trigger AS $$
DECLARE v_cap integer; v_ass integer;
BEGIN
  SELECT capacity, assigned INTO v_cap, v_ass
  FROM event
  WHERE id = NEW.event_id
  FOR UPDATE;

  IF v_cap IS NULL THEN
    RAISE EXCEPTION 'Event % not found', NEW.event_id;
  END IF;

  IF v_ass >= v_cap THEN
    RAISE EXCEPTION 'Event % is full (%/%).', NEW.event_id, v_ass, v_cap;
  END IF;

  UPDATE event SET assigned = v_ass + 1 WHERE id = NEW.event_id;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION fn_event_volunteer_after_delete()
RETURNS trigger AS $$
BEGIN
  UPDATE event
  SET assigned = GREATEST(assigned - 1, 0)
  WHERE id = OLD.event_id;
  RETURN OLD;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION fn_event_volunteer_before_update()
RETURNS trigger AS $$
DECLARE v_cap integer; v_ass integer;
BEGIN
  IF NEW.event_id = OLD.event_id THEN
    RETURN NEW;
  END IF;

  UPDATE event
  SET assigned = GREATEST(assigned - 1, 0)
  WHERE id = OLD.event_id;

  SELECT capacity, assigned INTO v_cap, v_ass
  FROM event
  WHERE id = NEW.event_id
  FOR UPDATE;

  IF v_cap IS NULL THEN
    RAISE EXCEPTION 'Event % not found', NEW.event_id;
  END IF;

  IF v_ass >= v_cap THEN
    RAISE EXCEPTION 'Event % is full (%/%).', NEW.event_id, v_ass, v_cap;
  END IF;

  UPDATE event SET assigned = v_ass + 1 WHERE id = NEW.event_id;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION fn_event_assigned_guard()
RETURNS trigger AS $$
BEGIN
  IF NEW.assigned <> OLD.assigned THEN
    RAISE EXCEPTION 'Direct updates to event.assigned are not allowed';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Recreate triggers idempotently
DROP TRIGGER IF EXISTS trg_event_volunteer_bi ON event_volunteer;
CREATE TRIGGER trg_event_volunteer_bi
  BEFORE INSERT ON event_volunteer
  FOR EACH ROW EXECUTE FUNCTION fn_event_volunteer_before_insert();

DROP TRIGGER IF EXISTS trg_event_volunteer_bd ON event_volunteer;
CREATE TRIGGER trg_event_volunteer_bd
  AFTER DELETE ON event_volunteer
  FOR EACH ROW EXECUTE FUNCTION fn_event_volunteer_after_delete();

DROP TRIGGER IF EXISTS trg_event_volunteer_bu ON event_volunteer;
CREATE TRIGGER trg_event_volunteer_bu
  BEFORE UPDATE ON event_volunteer
  FOR EACH ROW EXECUTE FUNCTION fn_event_volunteer_before_update();

DROP TRIGGER IF EXISTS trg_event_assigned_guard ON event;
CREATE TRIGGER trg_event_assigned_guard
  BEFORE UPDATE OF assigned ON event
  FOR EACH ROW EXECUTE FUNCTION fn_event_assigned_guard();
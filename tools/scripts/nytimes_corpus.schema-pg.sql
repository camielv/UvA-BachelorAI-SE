--
-- PostgreSQL database dump
--

SET client_encoding = 'UTF8';
SET standard_conforming_strings = off;
SET check_function_bodies = false;
SET client_min_messages = warning;
SET escape_string_warning = off;

--
-- Name: plpgsql; Type: PROCEDURAL LANGUAGE; Schema: -; Owner: tsagias
--

CREATE PROCEDURAL LANGUAGE plpgsql;


ALTER PROCEDURAL LANGUAGE plpgsql OWNER TO tsagias;

SET search_path = public, pg_catalog;

SET default_tablespace = '';

SET default_with_oids = false;

--
-- Name: articles; Type: TABLE; Schema: public; Owner: tsagias; Tablespace: 
--

CREATE TABLE articles (
    article_id character varying NOT NULL,
    pubdate timestamp without time zone NOT NULL,
    title character varying,
    text character varying
);


ALTER TABLE public.articles OWNER TO tsagias;

--
-- Name: articles2groups; Type: TABLE; Schema: public; Owner: tsagias; Tablespace: 
--

CREATE TABLE articles2groups (
    article_id character varying NOT NULL,
    group_id integer NOT NULL
);


ALTER TABLE public.articles2groups OWNER TO tsagias;

--
-- Name: articles2taxonomy; Type: TABLE; Schema: public; Owner: tsagias; Tablespace: 
--

CREATE TABLE articles2taxonomy (
    article_id character varying NOT NULL,
    taxonomy_id integer NOT NULL
);


ALTER TABLE public.articles2taxonomy OWNER TO tsagias;

--
-- Name: groups; Type: TABLE; Schema: public; Owner: tsagias; Tablespace: 
--

CREATE TABLE groups (
    group_id integer NOT NULL,
    group_name character varying NOT NULL,
    group_type_id integer DEFAULT 0 NOT NULL
);


ALTER TABLE public.groups OWNER TO tsagias;

--
-- Name: TABLE groups; Type: COMMENT; Schema: public; Owner: tsagias
--

COMMENT ON TABLE groups IS '0 for stories
1 for categories';


--
-- Name: category_stats; Type: VIEW; Schema: public; Owner: tsagias
--

CREATE VIEW category_stats AS
    SELECT g.group_id AS category_id, g.group_name AS category, min(a.pubdate) AS startdate, max(a.pubdate) AS enddate, count(a2g.article_id) AS articles FROM ((groups g JOIN articles2groups a2g ON ((a2g.group_id = g.group_id))) JOIN articles a ON (((a.article_id)::text = (a2g.article_id)::text))) WHERE (g.group_type_id = 1) GROUP BY g.group_id, g.group_name, g.group_type_id;


ALTER TABLE public.category_stats OWNER TO tsagias;

--
-- Name: cepoch; Type: TABLE; Schema: public; Owner: tsagias; Tablespace: 
--

CREATE TABLE cepoch (
    ep integer NOT NULL
);


ALTER TABLE public.cepoch OWNER TO tsagias;

--
-- Name: TABLE cepoch; Type: COMMENT; Schema: public; Owner: tsagias
--

COMMENT ON TABLE cepoch IS 'constant table of epochs for 365*4 days (4 years)';


--
-- Name: descriptor_stats; Type: VIEW; Schema: public; Owner: tsagias
--

CREATE VIEW descriptor_stats AS
    SELECT g.group_id AS descriptor_id, g.group_name AS descriptor, g.group_type_id AS decriptor_type_id, min(a.pubdate) AS startdate, max(a.pubdate) AS enddate, count(a2g.article_id) AS articles FROM ((groups g JOIN articles2groups a2g ON ((a2g.group_id = g.group_id))) JOIN articles a ON (((a.article_id)::text = (a2g.article_id)::text))) GROUP BY g.group_id, g.group_name, g.group_type_id;


ALTER TABLE public.descriptor_stats OWNER TO tsagias;

--
-- Name: group_types; Type: TABLE; Schema: public; Owner: tsagias; Tablespace: 
--

CREATE TABLE group_types (
    group_type_id integer NOT NULL,
    group_type character varying NOT NULL
);


ALTER TABLE public.group_types OWNER TO tsagias;

--
-- Name: TABLE group_types; Type: COMMENT; Schema: public; Owner: tsagias
--

COMMENT ON TABLE group_types IS '        Human descriptors:
        10 -- Biographical categories
        11 -- Descriptors
        12 -- Locations
        13 -- Names
        14 -- Organizations
        15 -- People
        16 -- Titles
    
        Computer generated descriptors:
        50 -- General online descriptors
        51 -- Online descriptors
        52 -- Online locations
        53 -- Online organizations
        54 -- Online people
        55 -- Online titles
';


--
-- Name: mv_descriptor_stats; Type: TABLE; Schema: public; Owner: tsagias; Tablespace: 
--

CREATE TABLE mv_descriptor_stats (
    descriptor_id integer NOT NULL,
    descriptor character varying NOT NULL,
    descriptor_type_id integer NOT NULL,
    startdate timestamp without time zone NOT NULL,
    enddate timestamp without time zone NOT NULL,
    articles integer DEFAULT 0 NOT NULL
);


ALTER TABLE public.mv_descriptor_stats OWNER TO tsagias;

--
-- Name: story_stats; Type: VIEW; Schema: public; Owner: tsagias
--

CREATE VIEW story_stats AS
    SELECT g.group_id AS story_id, g.group_name AS story, min(a.pubdate) AS startdate, max(a.pubdate) AS enddate, count(a2g.article_id) AS articles FROM ((groups g JOIN articles2groups a2g ON ((a2g.group_id = g.group_id))) JOIN articles a ON (((a.article_id)::text = (a2g.article_id)::text))) WHERE (g.group_type_id = 0) GROUP BY g.group_id, g.group_name, g.group_type_id;


ALTER TABLE public.story_stats OWNER TO tsagias;

--
-- Name: taxonomy; Type: TABLE; Schema: public; Owner: tsagias; Tablespace: 
--

CREATE TABLE taxonomy (
    taxonomy_id integer NOT NULL,
    taxonomy_name character varying NOT NULL,
    taxonomy_parent_id integer
);


ALTER TABLE public.taxonomy OWNER TO tsagias;

--
-- Name: topics_fft_coeff_index; Type: TABLE; Schema: public; Owner: tsagias; Tablespace: 
--

CREATE TABLE topics_fft_coeff_index (
    topic_id integer NOT NULL,
    coef_index character varying NOT NULL,
    power character varying NOT NULL,
    period character varying NOT NULL,
    freq character varying NOT NULL
);


ALTER TABLE public.topics_fft_coeff_index OWNER TO tsagias;

--
-- Name: add_article(character varying, date, character varying, character varying, character varying, character varying); Type: FUNCTION; Schema: public; Owner: tsagias
--

CREATE FUNCTION add_article(_url character varying, _date date, _cats character varying, _title character varying, _summary character varying, _topic character varying) RETURNS void
    AS $$
BEGIN
-- check if articles exists and insert it
IF NOT EXISTS(SELECT 1 FROM articles WHERE article_id = _url) THEN
	INSERT INTO articles (article_id, pubdate, title, text) VALUES (_url, _date, _title, _summary);
END IF;

-- link article to topic
PERFORM link_article_topic(_url, _topic);

-- link article to categories
IF _cats != '' THEN
	PERFORM link_article_categories(_url, _cats);
END IF;

END
$$
    LANGUAGE plpgsql;


ALTER FUNCTION public.add_article(_url character varying, _date date, _cats character varying, _title character varying, _summary character varying, _topic character varying) OWNER TO tsagias;

--
-- Name: articles2groups_check_existence(); Type: FUNCTION; Schema: public; Owner: tsagias
--

CREATE FUNCTION articles2groups_check_existence() RETURNS trigger
    AS $$
BEGIN
IF EXISTS (SELECT 1 FROM articles2groups WHERE article_id = new.article_id 
AND group_id = new.group_id) THEN
 RETURN NULL;
END IF;

RETURN NEW;
END;
$$
    LANGUAGE plpgsql;


ALTER FUNCTION public.articles2groups_check_existence() OWNER TO tsagias;

--
-- Name: groups_check_existence(); Type: FUNCTION; Schema: public; Owner: tsagias
--

CREATE FUNCTION groups_check_existence() RETURNS trigger
    AS $$
BEGIN
IF EXISTS (SELECT 1 FROM groups WHERE groups.group_name = new.group_name AND groups.group_type_id = new.group_type_id) THEN
 RETURN NULL;
END IF;

RETURN NEW;
END;
$$
    LANGUAGE plpgsql;


ALTER FUNCTION public.groups_check_existence() OWNER TO tsagias;

--
-- Name: link_article_categories(character varying, character varying); Type: FUNCTION; Schema: public; Owner: tsagias
--

CREATE FUNCTION link_article_categories(_url character varying, _cats character varying) RETURNS void
    AS $$
DECLARE
	_rcats varchar[];
	cat_id int;
BEGIN
-- categories come as comma separated string
-- split the string
_rcats := string_to_array(_cats, ',');
FOR i IN array_lower(_rcats,1) .. array_upper(_rcats,1) LOOP
	-- get category id
	SELECT INTO cat_id group_id FROM groups WHERE group_name = _rcats[i] AND group_type = 1; 
	-- check if category exists
	IF cat_id IS NULL THEN
		cat_id := nextval('groups_group_id_seq');
		INSERT INTO groups VALUES (cat_id, _rcats[i], 1);
	END IF;

	-- link article to cat_id
	BEGIN
		INSERT INTO articles2groups VALUES (_url, cat_id);
	EXCEPTION WHEN unique_violation THEN
            -- do nothing
	END;

END LOOP;

END
$$
    LANGUAGE plpgsql;


ALTER FUNCTION public.link_article_categories(_url character varying, _cats character varying) OWNER TO tsagias;

--
-- Name: link_article_topic(character varying, character varying); Type: FUNCTION; Schema: public; Owner: tsagias
--

CREATE FUNCTION link_article_topic(_url character varying, _topic character varying) RETURNS void
    AS $$
DECLARE
	topic_id int;
BEGIN
-- check if topic exists
SELECT INTO topic_id group_id FROM groups WHERE group_name = _topic AND group_type = 0;
IF topic_id IS NULL THEN
	topic_id  := nextval('groups_group_id_seq');
	INSERT INTO groups VALUES (topic_id, _topic, 0);
END IF;

BEGIN
	INSERT INTO articles2groups VALUES(_url, topic_id);
EXCEPTION WHEN unique_violation THEN
            -- do nothing
END;
	
END
$$
    LANGUAGE plpgsql;


ALTER FUNCTION public.link_article_topic(_url character varying, _topic character varying) OWNER TO tsagias;

--
-- Name: taxonomy_children_of(integer); Type: FUNCTION; Schema: public; Owner: tsagias
--

CREATE FUNCTION taxonomy_children_of(_taxonomy_id integer) RETURNS SETOF integer
    AS $$
DECLARE 
	__taxonomy_id integer;
BEGIN
RAISE INFO 'Processing children of child: %', _taxonomy_id;
RETURN NEXT _taxonomy_id;
-- GET THE TAXONOMY CHILDREN
FOR __taxonomy_id IN SELECT taxonomy_id FROM taxonomy WHERE taxonomy_parent_id = _taxonomy_id LOOP
	RETURN NEXT taxonomy_children_of(__taxonomy_id);
END LOOP;
RETURN;
END;
$$
    LANGUAGE plpgsql;


ALTER FUNCTION public.taxonomy_children_of(_taxonomy_id integer) OWNER TO tsagias;

--
-- Name: array_accum(anyelement); Type: AGGREGATE; Schema: public; Owner: tsagias
--

CREATE AGGREGATE array_accum(anyelement) (
    SFUNC = array_append,
    STYPE = anyarray,
    INITCOND = '{}'
);


ALTER AGGREGATE public.array_accum(anyelement) OWNER TO tsagias;

--
-- Name: groups_group_id_seq; Type: SEQUENCE; Schema: public; Owner: tsagias
--

CREATE SEQUENCE groups_group_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;


ALTER TABLE public.groups_group_id_seq OWNER TO tsagias;

--
-- Name: groups_group_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: tsagias
--

ALTER SEQUENCE groups_group_id_seq OWNED BY groups.group_id;


--
-- Name: taxonomy_taxonomy_id_seq; Type: SEQUENCE; Schema: public; Owner: tsagias
--

CREATE SEQUENCE taxonomy_taxonomy_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;


ALTER TABLE public.taxonomy_taxonomy_id_seq OWNER TO tsagias;

--
-- Name: taxonomy_taxonomy_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: tsagias
--

ALTER SEQUENCE taxonomy_taxonomy_id_seq OWNED BY taxonomy.taxonomy_id;


--
-- Name: group_id; Type: DEFAULT; Schema: public; Owner: tsagias
--

ALTER TABLE groups ALTER COLUMN group_id SET DEFAULT nextval('groups_group_id_seq'::regclass);


--
-- Name: taxonomy_id; Type: DEFAULT; Schema: public; Owner: tsagias
--

ALTER TABLE taxonomy ALTER COLUMN taxonomy_id SET DEFAULT nextval('taxonomy_taxonomy_id_seq'::regclass);


--
-- Name: articles2groups_pkey; Type: CONSTRAINT; Schema: public; Owner: tsagias; Tablespace: 
--

ALTER TABLE ONLY articles2groups
    ADD CONSTRAINT articles2groups_pkey PRIMARY KEY (article_id, group_id);


--
-- Name: articles2taxonomy_pkey; Type: CONSTRAINT; Schema: public; Owner: tsagias; Tablespace: 
--

ALTER TABLE ONLY articles2taxonomy
    ADD CONSTRAINT articles2taxonomy_pkey PRIMARY KEY (article_id, taxonomy_id);


--
-- Name: articles_pkey; Type: CONSTRAINT; Schema: public; Owner: tsagias; Tablespace: 
--

ALTER TABLE ONLY articles
    ADD CONSTRAINT articles_pkey PRIMARY KEY (article_id);


--
-- Name: cepoch_pkey; Type: CONSTRAINT; Schema: public; Owner: tsagias; Tablespace: 
--

ALTER TABLE ONLY cepoch
    ADD CONSTRAINT cepoch_pkey PRIMARY KEY (ep);


--
-- Name: group_types_pkey; Type: CONSTRAINT; Schema: public; Owner: tsagias; Tablespace: 
--

ALTER TABLE ONLY group_types
    ADD CONSTRAINT group_types_pkey PRIMARY KEY (group_type_id);


--
-- Name: groups_pkey; Type: CONSTRAINT; Schema: public; Owner: tsagias; Tablespace: 
--

ALTER TABLE ONLY groups
    ADD CONSTRAINT groups_pkey PRIMARY KEY (group_id);


--
-- Name: groups_uniq_idx; Type: CONSTRAINT; Schema: public; Owner: tsagias; Tablespace: 
--

ALTER TABLE ONLY groups
    ADD CONSTRAINT groups_uniq_idx UNIQUE (group_name, group_type_id);


--
-- Name: mv_descriptor_stats_pkey; Type: CONSTRAINT; Schema: public; Owner: tsagias; Tablespace: 
--

ALTER TABLE ONLY mv_descriptor_stats
    ADD CONSTRAINT mv_descriptor_stats_pkey PRIMARY KEY (descriptor_id);


--
-- Name: taxonomy_pkey; Type: CONSTRAINT; Schema: public; Owner: tsagias; Tablespace: 
--

ALTER TABLE ONLY taxonomy
    ADD CONSTRAINT taxonomy_pkey PRIMARY KEY (taxonomy_id);


--
-- Name: topics_fft_important_coeff_index_topic_id_pkey; Type: CONSTRAINT; Schema: public; Owner: tsagias; Tablespace: 
--

ALTER TABLE ONLY topics_fft_coeff_index
    ADD CONSTRAINT topics_fft_important_coeff_index_topic_id_pkey PRIMARY KEY (topic_id);


--
-- Name: articles2groups_articles_article_id_idx; Type: INDEX; Schema: public; Owner: tsagias; Tablespace: 
--

CREATE INDEX articles2groups_articles_article_id_idx ON articles2groups USING btree (article_id);


--
-- Name: articles_pubdate_idx; Type: INDEX; Schema: public; Owner: tsagias; Tablespace: 
--

CREATE INDEX articles_pubdate_idx ON articles USING btree (pubdate);


--
-- Name: fki_articles2groups_group_id_fkey; Type: INDEX; Schema: public; Owner: tsagias; Tablespace: 
--

CREATE INDEX fki_articles2groups_group_id_fkey ON articles2groups USING btree (group_id);


--
-- Name: fki_groups_group_type_id_fkey; Type: INDEX; Schema: public; Owner: tsagias; Tablespace: 
--

CREATE INDEX fki_groups_group_type_id_fkey ON groups USING btree (group_type_id);


--
-- Name: fki_taxonomy_parent_id_fkey; Type: INDEX; Schema: public; Owner: tsagias; Tablespace: 
--

CREATE INDEX fki_taxonomy_parent_id_fkey ON taxonomy USING btree (taxonomy_parent_id);


--
-- Name: mv_decriptor_stats_descriptor_type_id_idx; Type: INDEX; Schema: public; Owner: tsagias; Tablespace: 
--

CREATE INDEX mv_decriptor_stats_descriptor_type_id_idx ON mv_descriptor_stats USING btree (descriptor_type_id);


--
-- Name: mv_descriptor_stats_enddate_idx; Type: INDEX; Schema: public; Owner: tsagias; Tablespace: 
--

CREATE INDEX mv_descriptor_stats_enddate_idx ON mv_descriptor_stats USING btree (enddate);


--
-- Name: mv_descriptor_stats_startdate_idx; Type: INDEX; Schema: public; Owner: tsagias; Tablespace: 
--

CREATE INDEX mv_descriptor_stats_startdate_idx ON mv_descriptor_stats USING btree (startdate);


--
-- Name: taxonomy_name_parent_id_uniq; Type: INDEX; Schema: public; Owner: tsagias; Tablespace: 
--

CREATE UNIQUE INDEX taxonomy_name_parent_id_uniq ON taxonomy USING btree (taxonomy_name, taxonomy_parent_id);


--
-- Name: articles2groups_check_before_insert; Type: TRIGGER; Schema: public; Owner: tsagias
--

CREATE TRIGGER articles2groups_check_before_insert
    BEFORE INSERT ON articles2groups
    FOR EACH ROW
    EXECUTE PROCEDURE articles2groups_check_existence();


--
-- Name: groups_before_insert; Type: TRIGGER; Schema: public; Owner: tsagias
--

CREATE TRIGGER groups_before_insert
    BEFORE INSERT ON groups
    FOR EACH ROW
    EXECUTE PROCEDURE groups_check_existence();


--
-- Name: articles2groups_articles_article_id; Type: FK CONSTRAINT; Schema: public; Owner: tsagias
--

ALTER TABLE ONLY articles2groups
    ADD CONSTRAINT articles2groups_articles_article_id FOREIGN KEY (article_id) REFERENCES articles(article_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: articles2groups_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: tsagias
--

ALTER TABLE ONLY articles2groups
    ADD CONSTRAINT articles2groups_group_id_fkey FOREIGN KEY (group_id) REFERENCES groups(group_id);


--
-- Name: articles2taxonomies_taxonomy_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: tsagias
--

ALTER TABLE ONLY articles2taxonomy
    ADD CONSTRAINT articles2taxonomies_taxonomy_id_fkey FOREIGN KEY (taxonomy_id) REFERENCES taxonomy(taxonomy_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: articles2taxonomy_article_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: tsagias
--

ALTER TABLE ONLY articles2taxonomy
    ADD CONSTRAINT articles2taxonomy_article_id_fkey FOREIGN KEY (article_id) REFERENCES articles(article_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: groups_group_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: tsagias
--

ALTER TABLE ONLY groups
    ADD CONSTRAINT groups_group_type_id_fkey FOREIGN KEY (group_type_id) REFERENCES group_types(group_type_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: taxonomy_parent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: tsagias
--

ALTER TABLE ONLY taxonomy
    ADD CONSTRAINT taxonomy_parent_id_fkey FOREIGN KEY (taxonomy_parent_id) REFERENCES taxonomy(taxonomy_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: topics_fft_important_coeff_topic_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: tsagias
--

ALTER TABLE ONLY topics_fft_coeff_index
    ADD CONSTRAINT topics_fft_important_coeff_topic_id_fkey FOREIGN KEY (topic_id) REFERENCES groups(group_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: public; Type: ACL; Schema: -; Owner: tsagias
--

REVOKE ALL ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON SCHEMA public FROM tsagias;
GRANT ALL ON SCHEMA public TO tsagias;
GRANT ALL ON SCHEMA public TO PUBLIC;


--
-- PostgreSQL database dump complete
--


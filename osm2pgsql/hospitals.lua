local hospitals = osm2pgsql.define_table({
    name = 'hospitals',
    ids = { type = 'any', type_column = 'osm_type', id_column = 'osm_id' },
    columns = {
        { column = 'name', type = 'text' },
        { column = 'tags', type = 'jsonb' },
        { column = 'geom', type = 'point', projection = '4326' }
}})

-- from old output:
-- osm_id | addr:street | addr:housename | addr:housenumber | addr:city | addr:state | addr:postal_code | addr:interpolation |
-- amenity | name | cuisine | website | contact:website | contact:facebook | contact:instagram | brand:wikidata | way | centroid_geog

function process_object(object, geom)
    local r = {
        name = object.tags.name,
        amenity = object.tags.amenity,

	    tags = object.tags,
        geom = geom
    }

    if object.tags.amenity == "hospital" then
        hospitals:insert(r)
    end
end

function osm2pgsql.process_node(object)
    process_object(object, object:as_point())
end

function osm2pgsql.process_way(object)
    if object.is_closed then
        process_object(object, object:as_polygon():centroid())
    end
end

function osm2pgsql.process_relation(object)
    if object.tags.type == 'multipolygon' then
        process_object(object, object:as_multipolygon():centroid())
    end
end

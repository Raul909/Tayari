// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'basin.dart';

// **************************************************************************
// IsarCollectionGenerator
// **************************************************************************

// coverage:ignore-file
// ignore_for_file: duplicate_ignore, non_constant_identifier_names, constant_identifier_names, invalid_use_of_protected_member, unnecessary_cast, prefer_const_constructors, lines_longer_than_80_chars, require_trailing_commas, inference_failure_on_function_invocation, unnecessary_parenthesis, unnecessary_raw_strings, unnecessary_null_checks, join_return_with_assignment, prefer_final_locals, avoid_js_rounded_ints, avoid_positional_boolean_parameters, always_specify_types

extension GetBasinCollection on Isar {
  IsarCollection<Basin> get basins => this.collection();
}

const BasinSchema = CollectionSchema(
  name: r'Basin',
  id: -2185150921612653936,
  properties: {
    r'basinId': PropertySchema(
      id: 0,
      name: r'basinId',
      type: IsarType.string,
    ),
    r'country': PropertySchema(
      id: 1,
      name: r'country',
      type: IsarType.string,
    ),
    r'currentDischarge': PropertySchema(
      id: 2,
      name: r'currentDischarge',
      type: IsarType.double,
    ),
    r'currentRisk': PropertySchema(
      id: 3,
      name: r'currentRisk',
      type: IsarType.string,
    ),
    r'floodProbability': PropertySchema(
      id: 4,
      name: r'floodProbability',
      type: IsarType.double,
    ),
    r'latitude': PropertySchema(
      id: 5,
      name: r'latitude',
      type: IsarType.double,
    ),
    r'longitude': PropertySchema(
      id: 6,
      name: r'longitude',
      type: IsarType.double,
    ),
    r'name': PropertySchema(
      id: 7,
      name: r'name',
      type: IsarType.string,
    ),
    r'river': PropertySchema(
      id: 8,
      name: r'river',
      type: IsarType.string,
    )
  },
  estimateSize: _basinEstimateSize,
  serialize: _basinSerialize,
  deserialize: _basinDeserialize,
  deserializeProp: _basinDeserializeProp,
  idName: r'id',
  indexes: {
    r'basinId': IndexSchema(
      id: 4774926271971662280,
      name: r'basinId',
      unique: true,
      replace: true,
      properties: [
        IndexPropertySchema(
          name: r'basinId',
          type: IndexType.hash,
          caseSensitive: true,
        )
      ],
    )
  },
  links: {},
  embeddedSchemas: {},
  getId: _basinGetId,
  getLinks: _basinGetLinks,
  attach: _basinAttach,
  version: '3.1.0+1',
);

int _basinEstimateSize(
  Basin object,
  List<int> offsets,
  Map<Type, List<int>> allOffsets,
) {
  var bytesCount = offsets.last;
  bytesCount += 3 + object.basinId.length * 3;
  bytesCount += 3 + object.country.length * 3;
  bytesCount += 3 + object.currentRisk.length * 3;
  bytesCount += 3 + object.name.length * 3;
  bytesCount += 3 + object.river.length * 3;
  return bytesCount;
}

void _basinSerialize(
  Basin object,
  IsarWriter writer,
  List<int> offsets,
  Map<Type, List<int>> allOffsets,
) {
  writer.writeString(offsets[0], object.basinId);
  writer.writeString(offsets[1], object.country);
  writer.writeDouble(offsets[2], object.currentDischarge);
  writer.writeString(offsets[3], object.currentRisk);
  writer.writeDouble(offsets[4], object.floodProbability);
  writer.writeDouble(offsets[5], object.latitude);
  writer.writeDouble(offsets[6], object.longitude);
  writer.writeString(offsets[7], object.name);
  writer.writeString(offsets[8], object.river);
}

Basin _basinDeserialize(
  Id id,
  IsarReader reader,
  List<int> offsets,
  Map<Type, List<int>> allOffsets,
) {
  final object = Basin();
  object.basinId = reader.readString(offsets[0]);
  object.country = reader.readString(offsets[1]);
  object.currentDischarge = reader.readDouble(offsets[2]);
  object.currentRisk = reader.readString(offsets[3]);
  object.floodProbability = reader.readDoubleOrNull(offsets[4]);
  object.id = id;
  object.latitude = reader.readDouble(offsets[5]);
  object.longitude = reader.readDouble(offsets[6]);
  object.name = reader.readString(offsets[7]);
  object.river = reader.readString(offsets[8]);
  return object;
}

P _basinDeserializeProp<P>(
  IsarReader reader,
  int propertyId,
  int offset,
  Map<Type, List<int>> allOffsets,
) {
  switch (propertyId) {
    case 0:
      return (reader.readString(offset)) as P;
    case 1:
      return (reader.readString(offset)) as P;
    case 2:
      return (reader.readDouble(offset)) as P;
    case 3:
      return (reader.readString(offset)) as P;
    case 4:
      return (reader.readDoubleOrNull(offset)) as P;
    case 5:
      return (reader.readDouble(offset)) as P;
    case 6:
      return (reader.readDouble(offset)) as P;
    case 7:
      return (reader.readString(offset)) as P;
    case 8:
      return (reader.readString(offset)) as P;
    default:
      throw IsarError('Unknown property with id $propertyId');
  }
}

Id _basinGetId(Basin object) {
  return object.id;
}

List<IsarLinkBase<dynamic>> _basinGetLinks(Basin object) {
  return [];
}

void _basinAttach(IsarCollection<dynamic> col, Id id, Basin object) {
  object.id = id;
}

extension BasinByIndex on IsarCollection<Basin> {
  Future<Basin?> getByBasinId(String basinId) {
    return getByIndex(r'basinId', [basinId]);
  }

  Basin? getByBasinIdSync(String basinId) {
    return getByIndexSync(r'basinId', [basinId]);
  }

  Future<bool> deleteByBasinId(String basinId) {
    return deleteByIndex(r'basinId', [basinId]);
  }

  bool deleteByBasinIdSync(String basinId) {
    return deleteByIndexSync(r'basinId', [basinId]);
  }

  Future<List<Basin?>> getAllByBasinId(List<String> basinIdValues) {
    final values = basinIdValues.map((e) => [e]).toList();
    return getAllByIndex(r'basinId', values);
  }

  List<Basin?> getAllByBasinIdSync(List<String> basinIdValues) {
    final values = basinIdValues.map((e) => [e]).toList();
    return getAllByIndexSync(r'basinId', values);
  }

  Future<int> deleteAllByBasinId(List<String> basinIdValues) {
    final values = basinIdValues.map((e) => [e]).toList();
    return deleteAllByIndex(r'basinId', values);
  }

  int deleteAllByBasinIdSync(List<String> basinIdValues) {
    final values = basinIdValues.map((e) => [e]).toList();
    return deleteAllByIndexSync(r'basinId', values);
  }

  Future<Id> putByBasinId(Basin object) {
    return putByIndex(r'basinId', object);
  }

  Id putByBasinIdSync(Basin object, {bool saveLinks = true}) {
    return putByIndexSync(r'basinId', object, saveLinks: saveLinks);
  }

  Future<List<Id>> putAllByBasinId(List<Basin> objects) {
    return putAllByIndex(r'basinId', objects);
  }

  List<Id> putAllByBasinIdSync(List<Basin> objects, {bool saveLinks = true}) {
    return putAllByIndexSync(r'basinId', objects, saveLinks: saveLinks);
  }
}

extension BasinQueryWhereSort on QueryBuilder<Basin, Basin, QWhere> {
  QueryBuilder<Basin, Basin, QAfterWhere> anyId() {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(const IdWhereClause.any());
    });
  }
}

extension BasinQueryWhere on QueryBuilder<Basin, Basin, QWhereClause> {
  QueryBuilder<Basin, Basin, QAfterWhereClause> idEqualTo(Id id) {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(IdWhereClause.between(
        lower: id,
        upper: id,
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterWhereClause> idNotEqualTo(Id id) {
    return QueryBuilder.apply(this, (query) {
      if (query.whereSort == Sort.asc) {
        return query
            .addWhereClause(
              IdWhereClause.lessThan(upper: id, includeUpper: false),
            )
            .addWhereClause(
              IdWhereClause.greaterThan(lower: id, includeLower: false),
            );
      } else {
        return query
            .addWhereClause(
              IdWhereClause.greaterThan(lower: id, includeLower: false),
            )
            .addWhereClause(
              IdWhereClause.lessThan(upper: id, includeUpper: false),
            );
      }
    });
  }

  QueryBuilder<Basin, Basin, QAfterWhereClause> idGreaterThan(Id id,
      {bool include = false}) {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(
        IdWhereClause.greaterThan(lower: id, includeLower: include),
      );
    });
  }

  QueryBuilder<Basin, Basin, QAfterWhereClause> idLessThan(Id id,
      {bool include = false}) {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(
        IdWhereClause.lessThan(upper: id, includeUpper: include),
      );
    });
  }

  QueryBuilder<Basin, Basin, QAfterWhereClause> idBetween(
    Id lowerId,
    Id upperId, {
    bool includeLower = true,
    bool includeUpper = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(IdWhereClause.between(
        lower: lowerId,
        includeLower: includeLower,
        upper: upperId,
        includeUpper: includeUpper,
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterWhereClause> basinIdEqualTo(String basinId) {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(IndexWhereClause.equalTo(
        indexName: r'basinId',
        value: [basinId],
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterWhereClause> basinIdNotEqualTo(
      String basinId) {
    return QueryBuilder.apply(this, (query) {
      if (query.whereSort == Sort.asc) {
        return query
            .addWhereClause(IndexWhereClause.between(
              indexName: r'basinId',
              lower: [],
              upper: [basinId],
              includeUpper: false,
            ))
            .addWhereClause(IndexWhereClause.between(
              indexName: r'basinId',
              lower: [basinId],
              includeLower: false,
              upper: [],
            ));
      } else {
        return query
            .addWhereClause(IndexWhereClause.between(
              indexName: r'basinId',
              lower: [basinId],
              includeLower: false,
              upper: [],
            ))
            .addWhereClause(IndexWhereClause.between(
              indexName: r'basinId',
              lower: [],
              upper: [basinId],
              includeUpper: false,
            ));
      }
    });
  }
}

extension BasinQueryFilter on QueryBuilder<Basin, Basin, QFilterCondition> {
  QueryBuilder<Basin, Basin, QAfterFilterCondition> basinIdEqualTo(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'basinId',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> basinIdGreaterThan(
    String value, {
    bool include = false,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        include: include,
        property: r'basinId',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> basinIdLessThan(
    String value, {
    bool include = false,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.lessThan(
        include: include,
        property: r'basinId',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> basinIdBetween(
    String lower,
    String upper, {
    bool includeLower = true,
    bool includeUpper = true,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.between(
        property: r'basinId',
        lower: lower,
        includeLower: includeLower,
        upper: upper,
        includeUpper: includeUpper,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> basinIdStartsWith(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.startsWith(
        property: r'basinId',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> basinIdEndsWith(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.endsWith(
        property: r'basinId',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> basinIdContains(
      String value,
      {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.contains(
        property: r'basinId',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> basinIdMatches(
      String pattern,
      {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.matches(
        property: r'basinId',
        wildcard: pattern,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> basinIdIsEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'basinId',
        value: '',
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> basinIdIsNotEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        property: r'basinId',
        value: '',
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> countryEqualTo(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'country',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> countryGreaterThan(
    String value, {
    bool include = false,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        include: include,
        property: r'country',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> countryLessThan(
    String value, {
    bool include = false,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.lessThan(
        include: include,
        property: r'country',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> countryBetween(
    String lower,
    String upper, {
    bool includeLower = true,
    bool includeUpper = true,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.between(
        property: r'country',
        lower: lower,
        includeLower: includeLower,
        upper: upper,
        includeUpper: includeUpper,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> countryStartsWith(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.startsWith(
        property: r'country',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> countryEndsWith(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.endsWith(
        property: r'country',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> countryContains(
      String value,
      {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.contains(
        property: r'country',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> countryMatches(
      String pattern,
      {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.matches(
        property: r'country',
        wildcard: pattern,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> countryIsEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'country',
        value: '',
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> countryIsNotEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        property: r'country',
        value: '',
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> currentDischargeEqualTo(
    double value, {
    double epsilon = Query.epsilon,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'currentDischarge',
        value: value,
        epsilon: epsilon,
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> currentDischargeGreaterThan(
    double value, {
    bool include = false,
    double epsilon = Query.epsilon,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        include: include,
        property: r'currentDischarge',
        value: value,
        epsilon: epsilon,
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> currentDischargeLessThan(
    double value, {
    bool include = false,
    double epsilon = Query.epsilon,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.lessThan(
        include: include,
        property: r'currentDischarge',
        value: value,
        epsilon: epsilon,
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> currentDischargeBetween(
    double lower,
    double upper, {
    bool includeLower = true,
    bool includeUpper = true,
    double epsilon = Query.epsilon,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.between(
        property: r'currentDischarge',
        lower: lower,
        includeLower: includeLower,
        upper: upper,
        includeUpper: includeUpper,
        epsilon: epsilon,
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> currentRiskEqualTo(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'currentRisk',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> currentRiskGreaterThan(
    String value, {
    bool include = false,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        include: include,
        property: r'currentRisk',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> currentRiskLessThan(
    String value, {
    bool include = false,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.lessThan(
        include: include,
        property: r'currentRisk',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> currentRiskBetween(
    String lower,
    String upper, {
    bool includeLower = true,
    bool includeUpper = true,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.between(
        property: r'currentRisk',
        lower: lower,
        includeLower: includeLower,
        upper: upper,
        includeUpper: includeUpper,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> currentRiskStartsWith(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.startsWith(
        property: r'currentRisk',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> currentRiskEndsWith(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.endsWith(
        property: r'currentRisk',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> currentRiskContains(
      String value,
      {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.contains(
        property: r'currentRisk',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> currentRiskMatches(
      String pattern,
      {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.matches(
        property: r'currentRisk',
        wildcard: pattern,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> currentRiskIsEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'currentRisk',
        value: '',
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> currentRiskIsNotEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        property: r'currentRisk',
        value: '',
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> floodProbabilityIsNull() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(const FilterCondition.isNull(
        property: r'floodProbability',
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition>
      floodProbabilityIsNotNull() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(const FilterCondition.isNotNull(
        property: r'floodProbability',
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> floodProbabilityEqualTo(
    double? value, {
    double epsilon = Query.epsilon,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'floodProbability',
        value: value,
        epsilon: epsilon,
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> floodProbabilityGreaterThan(
    double? value, {
    bool include = false,
    double epsilon = Query.epsilon,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        include: include,
        property: r'floodProbability',
        value: value,
        epsilon: epsilon,
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> floodProbabilityLessThan(
    double? value, {
    bool include = false,
    double epsilon = Query.epsilon,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.lessThan(
        include: include,
        property: r'floodProbability',
        value: value,
        epsilon: epsilon,
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> floodProbabilityBetween(
    double? lower,
    double? upper, {
    bool includeLower = true,
    bool includeUpper = true,
    double epsilon = Query.epsilon,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.between(
        property: r'floodProbability',
        lower: lower,
        includeLower: includeLower,
        upper: upper,
        includeUpper: includeUpper,
        epsilon: epsilon,
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> idEqualTo(Id value) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'id',
        value: value,
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> idGreaterThan(
    Id value, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        include: include,
        property: r'id',
        value: value,
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> idLessThan(
    Id value, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.lessThan(
        include: include,
        property: r'id',
        value: value,
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> idBetween(
    Id lower,
    Id upper, {
    bool includeLower = true,
    bool includeUpper = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.between(
        property: r'id',
        lower: lower,
        includeLower: includeLower,
        upper: upper,
        includeUpper: includeUpper,
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> latitudeEqualTo(
    double value, {
    double epsilon = Query.epsilon,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'latitude',
        value: value,
        epsilon: epsilon,
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> latitudeGreaterThan(
    double value, {
    bool include = false,
    double epsilon = Query.epsilon,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        include: include,
        property: r'latitude',
        value: value,
        epsilon: epsilon,
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> latitudeLessThan(
    double value, {
    bool include = false,
    double epsilon = Query.epsilon,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.lessThan(
        include: include,
        property: r'latitude',
        value: value,
        epsilon: epsilon,
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> latitudeBetween(
    double lower,
    double upper, {
    bool includeLower = true,
    bool includeUpper = true,
    double epsilon = Query.epsilon,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.between(
        property: r'latitude',
        lower: lower,
        includeLower: includeLower,
        upper: upper,
        includeUpper: includeUpper,
        epsilon: epsilon,
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> longitudeEqualTo(
    double value, {
    double epsilon = Query.epsilon,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'longitude',
        value: value,
        epsilon: epsilon,
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> longitudeGreaterThan(
    double value, {
    bool include = false,
    double epsilon = Query.epsilon,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        include: include,
        property: r'longitude',
        value: value,
        epsilon: epsilon,
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> longitudeLessThan(
    double value, {
    bool include = false,
    double epsilon = Query.epsilon,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.lessThan(
        include: include,
        property: r'longitude',
        value: value,
        epsilon: epsilon,
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> longitudeBetween(
    double lower,
    double upper, {
    bool includeLower = true,
    bool includeUpper = true,
    double epsilon = Query.epsilon,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.between(
        property: r'longitude',
        lower: lower,
        includeLower: includeLower,
        upper: upper,
        includeUpper: includeUpper,
        epsilon: epsilon,
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> nameEqualTo(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'name',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> nameGreaterThan(
    String value, {
    bool include = false,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        include: include,
        property: r'name',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> nameLessThan(
    String value, {
    bool include = false,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.lessThan(
        include: include,
        property: r'name',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> nameBetween(
    String lower,
    String upper, {
    bool includeLower = true,
    bool includeUpper = true,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.between(
        property: r'name',
        lower: lower,
        includeLower: includeLower,
        upper: upper,
        includeUpper: includeUpper,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> nameStartsWith(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.startsWith(
        property: r'name',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> nameEndsWith(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.endsWith(
        property: r'name',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> nameContains(String value,
      {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.contains(
        property: r'name',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> nameMatches(String pattern,
      {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.matches(
        property: r'name',
        wildcard: pattern,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> nameIsEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'name',
        value: '',
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> nameIsNotEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        property: r'name',
        value: '',
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> riverEqualTo(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'river',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> riverGreaterThan(
    String value, {
    bool include = false,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        include: include,
        property: r'river',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> riverLessThan(
    String value, {
    bool include = false,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.lessThan(
        include: include,
        property: r'river',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> riverBetween(
    String lower,
    String upper, {
    bool includeLower = true,
    bool includeUpper = true,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.between(
        property: r'river',
        lower: lower,
        includeLower: includeLower,
        upper: upper,
        includeUpper: includeUpper,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> riverStartsWith(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.startsWith(
        property: r'river',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> riverEndsWith(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.endsWith(
        property: r'river',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> riverContains(String value,
      {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.contains(
        property: r'river',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> riverMatches(String pattern,
      {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.matches(
        property: r'river',
        wildcard: pattern,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> riverIsEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'river',
        value: '',
      ));
    });
  }

  QueryBuilder<Basin, Basin, QAfterFilterCondition> riverIsNotEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        property: r'river',
        value: '',
      ));
    });
  }
}

extension BasinQueryObject on QueryBuilder<Basin, Basin, QFilterCondition> {}

extension BasinQueryLinks on QueryBuilder<Basin, Basin, QFilterCondition> {}

extension BasinQuerySortBy on QueryBuilder<Basin, Basin, QSortBy> {
  QueryBuilder<Basin, Basin, QAfterSortBy> sortByBasinId() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'basinId', Sort.asc);
    });
  }

  QueryBuilder<Basin, Basin, QAfterSortBy> sortByBasinIdDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'basinId', Sort.desc);
    });
  }

  QueryBuilder<Basin, Basin, QAfterSortBy> sortByCountry() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'country', Sort.asc);
    });
  }

  QueryBuilder<Basin, Basin, QAfterSortBy> sortByCountryDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'country', Sort.desc);
    });
  }

  QueryBuilder<Basin, Basin, QAfterSortBy> sortByCurrentDischarge() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'currentDischarge', Sort.asc);
    });
  }

  QueryBuilder<Basin, Basin, QAfterSortBy> sortByCurrentDischargeDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'currentDischarge', Sort.desc);
    });
  }

  QueryBuilder<Basin, Basin, QAfterSortBy> sortByCurrentRisk() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'currentRisk', Sort.asc);
    });
  }

  QueryBuilder<Basin, Basin, QAfterSortBy> sortByCurrentRiskDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'currentRisk', Sort.desc);
    });
  }

  QueryBuilder<Basin, Basin, QAfterSortBy> sortByFloodProbability() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'floodProbability', Sort.asc);
    });
  }

  QueryBuilder<Basin, Basin, QAfterSortBy> sortByFloodProbabilityDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'floodProbability', Sort.desc);
    });
  }

  QueryBuilder<Basin, Basin, QAfterSortBy> sortByLatitude() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'latitude', Sort.asc);
    });
  }

  QueryBuilder<Basin, Basin, QAfterSortBy> sortByLatitudeDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'latitude', Sort.desc);
    });
  }

  QueryBuilder<Basin, Basin, QAfterSortBy> sortByLongitude() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'longitude', Sort.asc);
    });
  }

  QueryBuilder<Basin, Basin, QAfterSortBy> sortByLongitudeDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'longitude', Sort.desc);
    });
  }

  QueryBuilder<Basin, Basin, QAfterSortBy> sortByName() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'name', Sort.asc);
    });
  }

  QueryBuilder<Basin, Basin, QAfterSortBy> sortByNameDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'name', Sort.desc);
    });
  }

  QueryBuilder<Basin, Basin, QAfterSortBy> sortByRiver() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'river', Sort.asc);
    });
  }

  QueryBuilder<Basin, Basin, QAfterSortBy> sortByRiverDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'river', Sort.desc);
    });
  }
}

extension BasinQuerySortThenBy on QueryBuilder<Basin, Basin, QSortThenBy> {
  QueryBuilder<Basin, Basin, QAfterSortBy> thenByBasinId() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'basinId', Sort.asc);
    });
  }

  QueryBuilder<Basin, Basin, QAfterSortBy> thenByBasinIdDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'basinId', Sort.desc);
    });
  }

  QueryBuilder<Basin, Basin, QAfterSortBy> thenByCountry() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'country', Sort.asc);
    });
  }

  QueryBuilder<Basin, Basin, QAfterSortBy> thenByCountryDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'country', Sort.desc);
    });
  }

  QueryBuilder<Basin, Basin, QAfterSortBy> thenByCurrentDischarge() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'currentDischarge', Sort.asc);
    });
  }

  QueryBuilder<Basin, Basin, QAfterSortBy> thenByCurrentDischargeDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'currentDischarge', Sort.desc);
    });
  }

  QueryBuilder<Basin, Basin, QAfterSortBy> thenByCurrentRisk() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'currentRisk', Sort.asc);
    });
  }

  QueryBuilder<Basin, Basin, QAfterSortBy> thenByCurrentRiskDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'currentRisk', Sort.desc);
    });
  }

  QueryBuilder<Basin, Basin, QAfterSortBy> thenByFloodProbability() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'floodProbability', Sort.asc);
    });
  }

  QueryBuilder<Basin, Basin, QAfterSortBy> thenByFloodProbabilityDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'floodProbability', Sort.desc);
    });
  }

  QueryBuilder<Basin, Basin, QAfterSortBy> thenById() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'id', Sort.asc);
    });
  }

  QueryBuilder<Basin, Basin, QAfterSortBy> thenByIdDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'id', Sort.desc);
    });
  }

  QueryBuilder<Basin, Basin, QAfterSortBy> thenByLatitude() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'latitude', Sort.asc);
    });
  }

  QueryBuilder<Basin, Basin, QAfterSortBy> thenByLatitudeDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'latitude', Sort.desc);
    });
  }

  QueryBuilder<Basin, Basin, QAfterSortBy> thenByLongitude() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'longitude', Sort.asc);
    });
  }

  QueryBuilder<Basin, Basin, QAfterSortBy> thenByLongitudeDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'longitude', Sort.desc);
    });
  }

  QueryBuilder<Basin, Basin, QAfterSortBy> thenByName() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'name', Sort.asc);
    });
  }

  QueryBuilder<Basin, Basin, QAfterSortBy> thenByNameDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'name', Sort.desc);
    });
  }

  QueryBuilder<Basin, Basin, QAfterSortBy> thenByRiver() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'river', Sort.asc);
    });
  }

  QueryBuilder<Basin, Basin, QAfterSortBy> thenByRiverDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'river', Sort.desc);
    });
  }
}

extension BasinQueryWhereDistinct on QueryBuilder<Basin, Basin, QDistinct> {
  QueryBuilder<Basin, Basin, QDistinct> distinctByBasinId(
      {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'basinId', caseSensitive: caseSensitive);
    });
  }

  QueryBuilder<Basin, Basin, QDistinct> distinctByCountry(
      {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'country', caseSensitive: caseSensitive);
    });
  }

  QueryBuilder<Basin, Basin, QDistinct> distinctByCurrentDischarge() {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'currentDischarge');
    });
  }

  QueryBuilder<Basin, Basin, QDistinct> distinctByCurrentRisk(
      {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'currentRisk', caseSensitive: caseSensitive);
    });
  }

  QueryBuilder<Basin, Basin, QDistinct> distinctByFloodProbability() {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'floodProbability');
    });
  }

  QueryBuilder<Basin, Basin, QDistinct> distinctByLatitude() {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'latitude');
    });
  }

  QueryBuilder<Basin, Basin, QDistinct> distinctByLongitude() {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'longitude');
    });
  }

  QueryBuilder<Basin, Basin, QDistinct> distinctByName(
      {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'name', caseSensitive: caseSensitive);
    });
  }

  QueryBuilder<Basin, Basin, QDistinct> distinctByRiver(
      {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'river', caseSensitive: caseSensitive);
    });
  }
}

extension BasinQueryProperty on QueryBuilder<Basin, Basin, QQueryProperty> {
  QueryBuilder<Basin, int, QQueryOperations> idProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'id');
    });
  }

  QueryBuilder<Basin, String, QQueryOperations> basinIdProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'basinId');
    });
  }

  QueryBuilder<Basin, String, QQueryOperations> countryProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'country');
    });
  }

  QueryBuilder<Basin, double, QQueryOperations> currentDischargeProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'currentDischarge');
    });
  }

  QueryBuilder<Basin, String, QQueryOperations> currentRiskProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'currentRisk');
    });
  }

  QueryBuilder<Basin, double?, QQueryOperations> floodProbabilityProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'floodProbability');
    });
  }

  QueryBuilder<Basin, double, QQueryOperations> latitudeProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'latitude');
    });
  }

  QueryBuilder<Basin, double, QQueryOperations> longitudeProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'longitude');
    });
  }

  QueryBuilder<Basin, String, QQueryOperations> nameProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'name');
    });
  }

  QueryBuilder<Basin, String, QQueryOperations> riverProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'river');
    });
  }
}

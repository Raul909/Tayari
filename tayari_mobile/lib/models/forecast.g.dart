// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'forecast.dart';

// **************************************************************************
// IsarCollectionGenerator
// **************************************************************************

// coverage:ignore-file
// ignore_for_file: duplicate_ignore, non_constant_identifier_names, constant_identifier_names, invalid_use_of_protected_member, unnecessary_cast, prefer_const_constructors, lines_longer_than_80_chars, require_trailing_commas, inference_failure_on_function_invocation, unnecessary_parenthesis, unnecessary_raw_strings, unnecessary_null_checks, join_return_with_assignment, prefer_final_locals, avoid_js_rounded_ints, avoid_positional_boolean_parameters, always_specify_types

extension GetForecastCollection on Isar {
  IsarCollection<Forecast> get forecasts => this.collection();
}

const ForecastSchema = CollectionSchema(
  name: r'Forecast',
  id: -1049580500477324797,
  properties: {
    r'advisoryKeys': PropertySchema(
      id: 0,
      name: r'advisoryKeys',
      type: IsarType.stringList,
    ),
    r'advisoryValues': PropertySchema(
      id: 1,
      name: r'advisoryValues',
      type: IsarType.stringList,
    ),
    r'basinId': PropertySchema(
      id: 2,
      name: r'basinId',
      type: IsarType.string,
    ),
    r'clinicsAtRisk': PropertySchema(
      id: 3,
      name: r'clinicsAtRisk',
      type: IsarType.long,
    ),
    r'dischargeSeries': PropertySchema(
      id: 4,
      name: r'dischargeSeries',
      type: IsarType.doubleList,
    ),
    r'floodThreshold': PropertySchema(
      id: 5,
      name: r'floodThreshold',
      type: IsarType.double,
    ),
    r'lastSynced': PropertySchema(
      id: 6,
      name: r'lastSynced',
      type: IsarType.dateTime,
    ),
    r'peopleAtRisk': PropertySchema(
      id: 7,
      name: r'peopleAtRisk',
      type: IsarType.long,
    ),
    r'probability': PropertySchema(
      id: 8,
      name: r'probability',
      type: IsarType.double,
    ),
    r'riskLevel': PropertySchema(
      id: 9,
      name: r'riskLevel',
      type: IsarType.string,
    ),
    r'schoolsAtRisk': PropertySchema(
      id: 10,
      name: r'schoolsAtRisk',
      type: IsarType.long,
    ),
    r'thresholdExceedanceDays': PropertySchema(
      id: 11,
      name: r'thresholdExceedanceDays',
      type: IsarType.long,
    )
  },
  estimateSize: _forecastEstimateSize,
  serialize: _forecastSerialize,
  deserialize: _forecastDeserialize,
  deserializeProp: _forecastDeserializeProp,
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
  getId: _forecastGetId,
  getLinks: _forecastGetLinks,
  attach: _forecastAttach,
  version: '3.1.0+1',
);

int _forecastEstimateSize(
  Forecast object,
  List<int> offsets,
  Map<Type, List<int>> allOffsets,
) {
  var bytesCount = offsets.last;
  bytesCount += 3 + object.advisoryKeys.length * 3;
  {
    for (var i = 0; i < object.advisoryKeys.length; i++) {
      final value = object.advisoryKeys[i];
      bytesCount += value.length * 3;
    }
  }
  bytesCount += 3 + object.advisoryValues.length * 3;
  {
    for (var i = 0; i < object.advisoryValues.length; i++) {
      final value = object.advisoryValues[i];
      bytesCount += value.length * 3;
    }
  }
  bytesCount += 3 + object.basinId.length * 3;
  bytesCount += 3 + object.dischargeSeries.length * 8;
  bytesCount += 3 + object.riskLevel.length * 3;
  return bytesCount;
}

void _forecastSerialize(
  Forecast object,
  IsarWriter writer,
  List<int> offsets,
  Map<Type, List<int>> allOffsets,
) {
  writer.writeStringList(offsets[0], object.advisoryKeys);
  writer.writeStringList(offsets[1], object.advisoryValues);
  writer.writeString(offsets[2], object.basinId);
  writer.writeLong(offsets[3], object.clinicsAtRisk);
  writer.writeDoubleList(offsets[4], object.dischargeSeries);
  writer.writeDouble(offsets[5], object.floodThreshold);
  writer.writeDateTime(offsets[6], object.lastSynced);
  writer.writeLong(offsets[7], object.peopleAtRisk);
  writer.writeDouble(offsets[8], object.probability);
  writer.writeString(offsets[9], object.riskLevel);
  writer.writeLong(offsets[10], object.schoolsAtRisk);
  writer.writeLong(offsets[11], object.thresholdExceedanceDays);
}

Forecast _forecastDeserialize(
  Id id,
  IsarReader reader,
  List<int> offsets,
  Map<Type, List<int>> allOffsets,
) {
  final object = Forecast();
  object.advisoryKeys = reader.readStringList(offsets[0]) ?? [];
  object.advisoryValues = reader.readStringList(offsets[1]) ?? [];
  object.basinId = reader.readString(offsets[2]);
  object.clinicsAtRisk = reader.readLong(offsets[3]);
  object.dischargeSeries = reader.readDoubleList(offsets[4]) ?? [];
  object.floodThreshold = reader.readDouble(offsets[5]);
  object.id = id;
  object.lastSynced = reader.readDateTime(offsets[6]);
  object.peopleAtRisk = reader.readLong(offsets[7]);
  object.probability = reader.readDouble(offsets[8]);
  object.riskLevel = reader.readString(offsets[9]);
  object.schoolsAtRisk = reader.readLong(offsets[10]);
  object.thresholdExceedanceDays = reader.readLongOrNull(offsets[11]);
  return object;
}

P _forecastDeserializeProp<P>(
  IsarReader reader,
  int propertyId,
  int offset,
  Map<Type, List<int>> allOffsets,
) {
  switch (propertyId) {
    case 0:
      return (reader.readStringList(offset) ?? []) as P;
    case 1:
      return (reader.readStringList(offset) ?? []) as P;
    case 2:
      return (reader.readString(offset)) as P;
    case 3:
      return (reader.readLong(offset)) as P;
    case 4:
      return (reader.readDoubleList(offset) ?? []) as P;
    case 5:
      return (reader.readDouble(offset)) as P;
    case 6:
      return (reader.readDateTime(offset)) as P;
    case 7:
      return (reader.readLong(offset)) as P;
    case 8:
      return (reader.readDouble(offset)) as P;
    case 9:
      return (reader.readString(offset)) as P;
    case 10:
      return (reader.readLong(offset)) as P;
    case 11:
      return (reader.readLongOrNull(offset)) as P;
    default:
      throw IsarError('Unknown property with id $propertyId');
  }
}

Id _forecastGetId(Forecast object) {
  return object.id;
}

List<IsarLinkBase<dynamic>> _forecastGetLinks(Forecast object) {
  return [];
}

void _forecastAttach(IsarCollection<dynamic> col, Id id, Forecast object) {
  object.id = id;
}

extension ForecastByIndex on IsarCollection<Forecast> {
  Future<Forecast?> getByBasinId(String basinId) {
    return getByIndex(r'basinId', [basinId]);
  }

  Forecast? getByBasinIdSync(String basinId) {
    return getByIndexSync(r'basinId', [basinId]);
  }

  Future<bool> deleteByBasinId(String basinId) {
    return deleteByIndex(r'basinId', [basinId]);
  }

  bool deleteByBasinIdSync(String basinId) {
    return deleteByIndexSync(r'basinId', [basinId]);
  }

  Future<List<Forecast?>> getAllByBasinId(List<String> basinIdValues) {
    final values = basinIdValues.map((e) => [e]).toList();
    return getAllByIndex(r'basinId', values);
  }

  List<Forecast?> getAllByBasinIdSync(List<String> basinIdValues) {
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

  Future<Id> putByBasinId(Forecast object) {
    return putByIndex(r'basinId', object);
  }

  Id putByBasinIdSync(Forecast object, {bool saveLinks = true}) {
    return putByIndexSync(r'basinId', object, saveLinks: saveLinks);
  }

  Future<List<Id>> putAllByBasinId(List<Forecast> objects) {
    return putAllByIndex(r'basinId', objects);
  }

  List<Id> putAllByBasinIdSync(List<Forecast> objects,
      {bool saveLinks = true}) {
    return putAllByIndexSync(r'basinId', objects, saveLinks: saveLinks);
  }
}

extension ForecastQueryWhereSort on QueryBuilder<Forecast, Forecast, QWhere> {
  QueryBuilder<Forecast, Forecast, QAfterWhere> anyId() {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(const IdWhereClause.any());
    });
  }
}

extension ForecastQueryWhere on QueryBuilder<Forecast, Forecast, QWhereClause> {
  QueryBuilder<Forecast, Forecast, QAfterWhereClause> idEqualTo(Id id) {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(IdWhereClause.between(
        lower: id,
        upper: id,
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterWhereClause> idNotEqualTo(Id id) {
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

  QueryBuilder<Forecast, Forecast, QAfterWhereClause> idGreaterThan(Id id,
      {bool include = false}) {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(
        IdWhereClause.greaterThan(lower: id, includeLower: include),
      );
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterWhereClause> idLessThan(Id id,
      {bool include = false}) {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(
        IdWhereClause.lessThan(upper: id, includeUpper: include),
      );
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterWhereClause> idBetween(
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

  QueryBuilder<Forecast, Forecast, QAfterWhereClause> basinIdEqualTo(
      String basinId) {
    return QueryBuilder.apply(this, (query) {
      return query.addWhereClause(IndexWhereClause.equalTo(
        indexName: r'basinId',
        value: [basinId],
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterWhereClause> basinIdNotEqualTo(
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

extension ForecastQueryFilter
    on QueryBuilder<Forecast, Forecast, QFilterCondition> {
  QueryBuilder<Forecast, Forecast, QAfterFilterCondition>
      advisoryKeysElementEqualTo(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'advisoryKeys',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition>
      advisoryKeysElementGreaterThan(
    String value, {
    bool include = false,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        include: include,
        property: r'advisoryKeys',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition>
      advisoryKeysElementLessThan(
    String value, {
    bool include = false,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.lessThan(
        include: include,
        property: r'advisoryKeys',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition>
      advisoryKeysElementBetween(
    String lower,
    String upper, {
    bool includeLower = true,
    bool includeUpper = true,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.between(
        property: r'advisoryKeys',
        lower: lower,
        includeLower: includeLower,
        upper: upper,
        includeUpper: includeUpper,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition>
      advisoryKeysElementStartsWith(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.startsWith(
        property: r'advisoryKeys',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition>
      advisoryKeysElementEndsWith(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.endsWith(
        property: r'advisoryKeys',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition>
      advisoryKeysElementContains(String value, {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.contains(
        property: r'advisoryKeys',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition>
      advisoryKeysElementMatches(String pattern, {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.matches(
        property: r'advisoryKeys',
        wildcard: pattern,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition>
      advisoryKeysElementIsEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'advisoryKeys',
        value: '',
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition>
      advisoryKeysElementIsNotEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        property: r'advisoryKeys',
        value: '',
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition>
      advisoryKeysLengthEqualTo(int length) {
    return QueryBuilder.apply(this, (query) {
      return query.listLength(
        r'advisoryKeys',
        length,
        true,
        length,
        true,
      );
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition>
      advisoryKeysIsEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.listLength(
        r'advisoryKeys',
        0,
        true,
        0,
        true,
      );
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition>
      advisoryKeysIsNotEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.listLength(
        r'advisoryKeys',
        0,
        false,
        999999,
        true,
      );
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition>
      advisoryKeysLengthLessThan(
    int length, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.listLength(
        r'advisoryKeys',
        0,
        true,
        length,
        include,
      );
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition>
      advisoryKeysLengthGreaterThan(
    int length, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.listLength(
        r'advisoryKeys',
        length,
        include,
        999999,
        true,
      );
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition>
      advisoryKeysLengthBetween(
    int lower,
    int upper, {
    bool includeLower = true,
    bool includeUpper = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.listLength(
        r'advisoryKeys',
        lower,
        includeLower,
        upper,
        includeUpper,
      );
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition>
      advisoryValuesElementEqualTo(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'advisoryValues',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition>
      advisoryValuesElementGreaterThan(
    String value, {
    bool include = false,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        include: include,
        property: r'advisoryValues',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition>
      advisoryValuesElementLessThan(
    String value, {
    bool include = false,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.lessThan(
        include: include,
        property: r'advisoryValues',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition>
      advisoryValuesElementBetween(
    String lower,
    String upper, {
    bool includeLower = true,
    bool includeUpper = true,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.between(
        property: r'advisoryValues',
        lower: lower,
        includeLower: includeLower,
        upper: upper,
        includeUpper: includeUpper,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition>
      advisoryValuesElementStartsWith(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.startsWith(
        property: r'advisoryValues',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition>
      advisoryValuesElementEndsWith(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.endsWith(
        property: r'advisoryValues',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition>
      advisoryValuesElementContains(String value, {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.contains(
        property: r'advisoryValues',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition>
      advisoryValuesElementMatches(String pattern,
          {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.matches(
        property: r'advisoryValues',
        wildcard: pattern,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition>
      advisoryValuesElementIsEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'advisoryValues',
        value: '',
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition>
      advisoryValuesElementIsNotEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        property: r'advisoryValues',
        value: '',
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition>
      advisoryValuesLengthEqualTo(int length) {
    return QueryBuilder.apply(this, (query) {
      return query.listLength(
        r'advisoryValues',
        length,
        true,
        length,
        true,
      );
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition>
      advisoryValuesIsEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.listLength(
        r'advisoryValues',
        0,
        true,
        0,
        true,
      );
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition>
      advisoryValuesIsNotEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.listLength(
        r'advisoryValues',
        0,
        false,
        999999,
        true,
      );
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition>
      advisoryValuesLengthLessThan(
    int length, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.listLength(
        r'advisoryValues',
        0,
        true,
        length,
        include,
      );
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition>
      advisoryValuesLengthGreaterThan(
    int length, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.listLength(
        r'advisoryValues',
        length,
        include,
        999999,
        true,
      );
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition>
      advisoryValuesLengthBetween(
    int lower,
    int upper, {
    bool includeLower = true,
    bool includeUpper = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.listLength(
        r'advisoryValues',
        lower,
        includeLower,
        upper,
        includeUpper,
      );
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition> basinIdEqualTo(
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

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition> basinIdGreaterThan(
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

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition> basinIdLessThan(
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

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition> basinIdBetween(
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

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition> basinIdStartsWith(
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

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition> basinIdEndsWith(
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

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition> basinIdContains(
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

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition> basinIdMatches(
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

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition> basinIdIsEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'basinId',
        value: '',
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition> basinIdIsNotEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        property: r'basinId',
        value: '',
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition> clinicsAtRiskEqualTo(
      int value) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'clinicsAtRisk',
        value: value,
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition>
      clinicsAtRiskGreaterThan(
    int value, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        include: include,
        property: r'clinicsAtRisk',
        value: value,
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition> clinicsAtRiskLessThan(
    int value, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.lessThan(
        include: include,
        property: r'clinicsAtRisk',
        value: value,
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition> clinicsAtRiskBetween(
    int lower,
    int upper, {
    bool includeLower = true,
    bool includeUpper = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.between(
        property: r'clinicsAtRisk',
        lower: lower,
        includeLower: includeLower,
        upper: upper,
        includeUpper: includeUpper,
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition>
      dischargeSeriesElementEqualTo(
    double value, {
    double epsilon = Query.epsilon,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'dischargeSeries',
        value: value,
        epsilon: epsilon,
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition>
      dischargeSeriesElementGreaterThan(
    double value, {
    bool include = false,
    double epsilon = Query.epsilon,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        include: include,
        property: r'dischargeSeries',
        value: value,
        epsilon: epsilon,
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition>
      dischargeSeriesElementLessThan(
    double value, {
    bool include = false,
    double epsilon = Query.epsilon,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.lessThan(
        include: include,
        property: r'dischargeSeries',
        value: value,
        epsilon: epsilon,
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition>
      dischargeSeriesElementBetween(
    double lower,
    double upper, {
    bool includeLower = true,
    bool includeUpper = true,
    double epsilon = Query.epsilon,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.between(
        property: r'dischargeSeries',
        lower: lower,
        includeLower: includeLower,
        upper: upper,
        includeUpper: includeUpper,
        epsilon: epsilon,
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition>
      dischargeSeriesLengthEqualTo(int length) {
    return QueryBuilder.apply(this, (query) {
      return query.listLength(
        r'dischargeSeries',
        length,
        true,
        length,
        true,
      );
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition>
      dischargeSeriesIsEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.listLength(
        r'dischargeSeries',
        0,
        true,
        0,
        true,
      );
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition>
      dischargeSeriesIsNotEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.listLength(
        r'dischargeSeries',
        0,
        false,
        999999,
        true,
      );
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition>
      dischargeSeriesLengthLessThan(
    int length, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.listLength(
        r'dischargeSeries',
        0,
        true,
        length,
        include,
      );
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition>
      dischargeSeriesLengthGreaterThan(
    int length, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.listLength(
        r'dischargeSeries',
        length,
        include,
        999999,
        true,
      );
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition>
      dischargeSeriesLengthBetween(
    int lower,
    int upper, {
    bool includeLower = true,
    bool includeUpper = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.listLength(
        r'dischargeSeries',
        lower,
        includeLower,
        upper,
        includeUpper,
      );
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition> floodThresholdEqualTo(
    double value, {
    double epsilon = Query.epsilon,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'floodThreshold',
        value: value,
        epsilon: epsilon,
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition>
      floodThresholdGreaterThan(
    double value, {
    bool include = false,
    double epsilon = Query.epsilon,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        include: include,
        property: r'floodThreshold',
        value: value,
        epsilon: epsilon,
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition>
      floodThresholdLessThan(
    double value, {
    bool include = false,
    double epsilon = Query.epsilon,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.lessThan(
        include: include,
        property: r'floodThreshold',
        value: value,
        epsilon: epsilon,
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition> floodThresholdBetween(
    double lower,
    double upper, {
    bool includeLower = true,
    bool includeUpper = true,
    double epsilon = Query.epsilon,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.between(
        property: r'floodThreshold',
        lower: lower,
        includeLower: includeLower,
        upper: upper,
        includeUpper: includeUpper,
        epsilon: epsilon,
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition> idEqualTo(Id value) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'id',
        value: value,
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition> idGreaterThan(
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

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition> idLessThan(
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

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition> idBetween(
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

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition> lastSyncedEqualTo(
      DateTime value) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'lastSynced',
        value: value,
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition> lastSyncedGreaterThan(
    DateTime value, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        include: include,
        property: r'lastSynced',
        value: value,
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition> lastSyncedLessThan(
    DateTime value, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.lessThan(
        include: include,
        property: r'lastSynced',
        value: value,
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition> lastSyncedBetween(
    DateTime lower,
    DateTime upper, {
    bool includeLower = true,
    bool includeUpper = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.between(
        property: r'lastSynced',
        lower: lower,
        includeLower: includeLower,
        upper: upper,
        includeUpper: includeUpper,
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition> peopleAtRiskEqualTo(
      int value) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'peopleAtRisk',
        value: value,
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition>
      peopleAtRiskGreaterThan(
    int value, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        include: include,
        property: r'peopleAtRisk',
        value: value,
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition> peopleAtRiskLessThan(
    int value, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.lessThan(
        include: include,
        property: r'peopleAtRisk',
        value: value,
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition> peopleAtRiskBetween(
    int lower,
    int upper, {
    bool includeLower = true,
    bool includeUpper = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.between(
        property: r'peopleAtRisk',
        lower: lower,
        includeLower: includeLower,
        upper: upper,
        includeUpper: includeUpper,
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition> probabilityEqualTo(
    double value, {
    double epsilon = Query.epsilon,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'probability',
        value: value,
        epsilon: epsilon,
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition>
      probabilityGreaterThan(
    double value, {
    bool include = false,
    double epsilon = Query.epsilon,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        include: include,
        property: r'probability',
        value: value,
        epsilon: epsilon,
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition> probabilityLessThan(
    double value, {
    bool include = false,
    double epsilon = Query.epsilon,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.lessThan(
        include: include,
        property: r'probability',
        value: value,
        epsilon: epsilon,
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition> probabilityBetween(
    double lower,
    double upper, {
    bool includeLower = true,
    bool includeUpper = true,
    double epsilon = Query.epsilon,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.between(
        property: r'probability',
        lower: lower,
        includeLower: includeLower,
        upper: upper,
        includeUpper: includeUpper,
        epsilon: epsilon,
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition> riskLevelEqualTo(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'riskLevel',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition> riskLevelGreaterThan(
    String value, {
    bool include = false,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        include: include,
        property: r'riskLevel',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition> riskLevelLessThan(
    String value, {
    bool include = false,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.lessThan(
        include: include,
        property: r'riskLevel',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition> riskLevelBetween(
    String lower,
    String upper, {
    bool includeLower = true,
    bool includeUpper = true,
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.between(
        property: r'riskLevel',
        lower: lower,
        includeLower: includeLower,
        upper: upper,
        includeUpper: includeUpper,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition> riskLevelStartsWith(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.startsWith(
        property: r'riskLevel',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition> riskLevelEndsWith(
    String value, {
    bool caseSensitive = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.endsWith(
        property: r'riskLevel',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition> riskLevelContains(
      String value,
      {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.contains(
        property: r'riskLevel',
        value: value,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition> riskLevelMatches(
      String pattern,
      {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.matches(
        property: r'riskLevel',
        wildcard: pattern,
        caseSensitive: caseSensitive,
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition> riskLevelIsEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'riskLevel',
        value: '',
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition>
      riskLevelIsNotEmpty() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        property: r'riskLevel',
        value: '',
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition> schoolsAtRiskEqualTo(
      int value) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'schoolsAtRisk',
        value: value,
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition>
      schoolsAtRiskGreaterThan(
    int value, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        include: include,
        property: r'schoolsAtRisk',
        value: value,
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition> schoolsAtRiskLessThan(
    int value, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.lessThan(
        include: include,
        property: r'schoolsAtRisk',
        value: value,
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition> schoolsAtRiskBetween(
    int lower,
    int upper, {
    bool includeLower = true,
    bool includeUpper = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.between(
        property: r'schoolsAtRisk',
        lower: lower,
        includeLower: includeLower,
        upper: upper,
        includeUpper: includeUpper,
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition>
      thresholdExceedanceDaysIsNull() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(const FilterCondition.isNull(
        property: r'thresholdExceedanceDays',
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition>
      thresholdExceedanceDaysIsNotNull() {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(const FilterCondition.isNotNull(
        property: r'thresholdExceedanceDays',
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition>
      thresholdExceedanceDaysEqualTo(int? value) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.equalTo(
        property: r'thresholdExceedanceDays',
        value: value,
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition>
      thresholdExceedanceDaysGreaterThan(
    int? value, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.greaterThan(
        include: include,
        property: r'thresholdExceedanceDays',
        value: value,
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition>
      thresholdExceedanceDaysLessThan(
    int? value, {
    bool include = false,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.lessThan(
        include: include,
        property: r'thresholdExceedanceDays',
        value: value,
      ));
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterFilterCondition>
      thresholdExceedanceDaysBetween(
    int? lower,
    int? upper, {
    bool includeLower = true,
    bool includeUpper = true,
  }) {
    return QueryBuilder.apply(this, (query) {
      return query.addFilterCondition(FilterCondition.between(
        property: r'thresholdExceedanceDays',
        lower: lower,
        includeLower: includeLower,
        upper: upper,
        includeUpper: includeUpper,
      ));
    });
  }
}

extension ForecastQueryObject
    on QueryBuilder<Forecast, Forecast, QFilterCondition> {}

extension ForecastQueryLinks
    on QueryBuilder<Forecast, Forecast, QFilterCondition> {}

extension ForecastQuerySortBy on QueryBuilder<Forecast, Forecast, QSortBy> {
  QueryBuilder<Forecast, Forecast, QAfterSortBy> sortByBasinId() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'basinId', Sort.asc);
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterSortBy> sortByBasinIdDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'basinId', Sort.desc);
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterSortBy> sortByClinicsAtRisk() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'clinicsAtRisk', Sort.asc);
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterSortBy> sortByClinicsAtRiskDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'clinicsAtRisk', Sort.desc);
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterSortBy> sortByFloodThreshold() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'floodThreshold', Sort.asc);
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterSortBy> sortByFloodThresholdDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'floodThreshold', Sort.desc);
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterSortBy> sortByLastSynced() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'lastSynced', Sort.asc);
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterSortBy> sortByLastSyncedDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'lastSynced', Sort.desc);
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterSortBy> sortByPeopleAtRisk() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'peopleAtRisk', Sort.asc);
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterSortBy> sortByPeopleAtRiskDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'peopleAtRisk', Sort.desc);
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterSortBy> sortByProbability() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'probability', Sort.asc);
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterSortBy> sortByProbabilityDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'probability', Sort.desc);
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterSortBy> sortByRiskLevel() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'riskLevel', Sort.asc);
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterSortBy> sortByRiskLevelDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'riskLevel', Sort.desc);
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterSortBy> sortBySchoolsAtRisk() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'schoolsAtRisk', Sort.asc);
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterSortBy> sortBySchoolsAtRiskDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'schoolsAtRisk', Sort.desc);
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterSortBy>
      sortByThresholdExceedanceDays() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'thresholdExceedanceDays', Sort.asc);
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterSortBy>
      sortByThresholdExceedanceDaysDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'thresholdExceedanceDays', Sort.desc);
    });
  }
}

extension ForecastQuerySortThenBy
    on QueryBuilder<Forecast, Forecast, QSortThenBy> {
  QueryBuilder<Forecast, Forecast, QAfterSortBy> thenByBasinId() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'basinId', Sort.asc);
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterSortBy> thenByBasinIdDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'basinId', Sort.desc);
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterSortBy> thenByClinicsAtRisk() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'clinicsAtRisk', Sort.asc);
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterSortBy> thenByClinicsAtRiskDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'clinicsAtRisk', Sort.desc);
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterSortBy> thenByFloodThreshold() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'floodThreshold', Sort.asc);
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterSortBy> thenByFloodThresholdDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'floodThreshold', Sort.desc);
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterSortBy> thenById() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'id', Sort.asc);
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterSortBy> thenByIdDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'id', Sort.desc);
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterSortBy> thenByLastSynced() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'lastSynced', Sort.asc);
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterSortBy> thenByLastSyncedDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'lastSynced', Sort.desc);
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterSortBy> thenByPeopleAtRisk() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'peopleAtRisk', Sort.asc);
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterSortBy> thenByPeopleAtRiskDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'peopleAtRisk', Sort.desc);
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterSortBy> thenByProbability() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'probability', Sort.asc);
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterSortBy> thenByProbabilityDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'probability', Sort.desc);
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterSortBy> thenByRiskLevel() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'riskLevel', Sort.asc);
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterSortBy> thenByRiskLevelDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'riskLevel', Sort.desc);
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterSortBy> thenBySchoolsAtRisk() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'schoolsAtRisk', Sort.asc);
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterSortBy> thenBySchoolsAtRiskDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'schoolsAtRisk', Sort.desc);
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterSortBy>
      thenByThresholdExceedanceDays() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'thresholdExceedanceDays', Sort.asc);
    });
  }

  QueryBuilder<Forecast, Forecast, QAfterSortBy>
      thenByThresholdExceedanceDaysDesc() {
    return QueryBuilder.apply(this, (query) {
      return query.addSortBy(r'thresholdExceedanceDays', Sort.desc);
    });
  }
}

extension ForecastQueryWhereDistinct
    on QueryBuilder<Forecast, Forecast, QDistinct> {
  QueryBuilder<Forecast, Forecast, QDistinct> distinctByAdvisoryKeys() {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'advisoryKeys');
    });
  }

  QueryBuilder<Forecast, Forecast, QDistinct> distinctByAdvisoryValues() {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'advisoryValues');
    });
  }

  QueryBuilder<Forecast, Forecast, QDistinct> distinctByBasinId(
      {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'basinId', caseSensitive: caseSensitive);
    });
  }

  QueryBuilder<Forecast, Forecast, QDistinct> distinctByClinicsAtRisk() {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'clinicsAtRisk');
    });
  }

  QueryBuilder<Forecast, Forecast, QDistinct> distinctByDischargeSeries() {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'dischargeSeries');
    });
  }

  QueryBuilder<Forecast, Forecast, QDistinct> distinctByFloodThreshold() {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'floodThreshold');
    });
  }

  QueryBuilder<Forecast, Forecast, QDistinct> distinctByLastSynced() {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'lastSynced');
    });
  }

  QueryBuilder<Forecast, Forecast, QDistinct> distinctByPeopleAtRisk() {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'peopleAtRisk');
    });
  }

  QueryBuilder<Forecast, Forecast, QDistinct> distinctByProbability() {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'probability');
    });
  }

  QueryBuilder<Forecast, Forecast, QDistinct> distinctByRiskLevel(
      {bool caseSensitive = true}) {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'riskLevel', caseSensitive: caseSensitive);
    });
  }

  QueryBuilder<Forecast, Forecast, QDistinct> distinctBySchoolsAtRisk() {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'schoolsAtRisk');
    });
  }

  QueryBuilder<Forecast, Forecast, QDistinct>
      distinctByThresholdExceedanceDays() {
    return QueryBuilder.apply(this, (query) {
      return query.addDistinctBy(r'thresholdExceedanceDays');
    });
  }
}

extension ForecastQueryProperty
    on QueryBuilder<Forecast, Forecast, QQueryProperty> {
  QueryBuilder<Forecast, int, QQueryOperations> idProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'id');
    });
  }

  QueryBuilder<Forecast, List<String>, QQueryOperations>
      advisoryKeysProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'advisoryKeys');
    });
  }

  QueryBuilder<Forecast, List<String>, QQueryOperations>
      advisoryValuesProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'advisoryValues');
    });
  }

  QueryBuilder<Forecast, String, QQueryOperations> basinIdProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'basinId');
    });
  }

  QueryBuilder<Forecast, int, QQueryOperations> clinicsAtRiskProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'clinicsAtRisk');
    });
  }

  QueryBuilder<Forecast, List<double>, QQueryOperations>
      dischargeSeriesProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'dischargeSeries');
    });
  }

  QueryBuilder<Forecast, double, QQueryOperations> floodThresholdProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'floodThreshold');
    });
  }

  QueryBuilder<Forecast, DateTime, QQueryOperations> lastSyncedProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'lastSynced');
    });
  }

  QueryBuilder<Forecast, int, QQueryOperations> peopleAtRiskProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'peopleAtRisk');
    });
  }

  QueryBuilder<Forecast, double, QQueryOperations> probabilityProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'probability');
    });
  }

  QueryBuilder<Forecast, String, QQueryOperations> riskLevelProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'riskLevel');
    });
  }

  QueryBuilder<Forecast, int, QQueryOperations> schoolsAtRiskProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'schoolsAtRisk');
    });
  }

  QueryBuilder<Forecast, int?, QQueryOperations>
      thresholdExceedanceDaysProperty() {
    return QueryBuilder.apply(this, (query) {
      return query.addPropertyName(r'thresholdExceedanceDays');
    });
  }
}

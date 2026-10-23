package com.gahyeonbot.application.knowledge;

import java.util.*;

/** Versioned domain/range rules; graph reachability is not a new factual assertion. */
public final class OntologySchema {
    private OntologySchema() {}
    public enum Type { PERSON, ORGANIZATION, PROJECT, TASK, DOCUMENT, TOPIC }
    public enum Relation {
        MEMBER_OF, RESPONSIBLE_FOR, PART_OF, DEPENDS_ON, USES, ABOUT;

        public boolean accepts(Type subject, Type object) {
            return switch (this) {
                case MEMBER_OF -> subject == Type.PERSON && object == Type.ORGANIZATION;
                case RESPONSIBLE_FOR -> subject == Type.PERSON && Set.of(Type.PROJECT, Type.TASK).contains(object);
                case PART_OF -> subject == Type.TASK && object == Type.PROJECT
                        || subject == Type.PROJECT && object == Type.ORGANIZATION;
                case DEPENDS_ON -> subject == object && Set.of(Type.PROJECT, Type.TASK).contains(subject);
                case USES -> subject == Type.PROJECT && object == Type.TOPIC;
                case ABOUT -> subject == Type.DOCUMENT && Set.of(Type.PROJECT, Type.TOPIC).contains(object);
            };
        }
    }

    public record Entity(String key, Type type, String label, List<String> aliases) {
        public Entity {
            if (key == null || !key.matches("[a-zA-Z0-9][a-zA-Z0-9:._/-]{0,159}") || type == null)
                throw new IllegalArgumentException("Invalid ontology entity identity");
            label = text(label, 160);
            aliases = aliases == null ? List.of() : List.copyOf(aliases);
            if (aliases.size() > 8) throw new IllegalArgumentException("Too many entity aliases");
            aliases = aliases.stream().map(value -> text(value, 160)).distinct().toList();
        }
        public String identity() { return type.name() + ":" + key; }
        public List<String> names() {
            List<String> names = new ArrayList<>(aliases);
            names.add(label);
            return List.copyOf(names);
        }
    }

    public record Claim(Entity subject, Relation relation, Entity object, String evidenceQuote) {
        public Claim {
            Objects.requireNonNull(subject, "subject");
            Objects.requireNonNull(object, "object");
            if (relation == null || !relation.accepts(subject.type(), object.type()))
                throw new IllegalArgumentException("Ontology relation violates domain/range");
            if (subject.identity().equals(object.identity())) throw new IllegalArgumentException("Self relation not supported");
            evidenceQuote = text(evidenceQuote, 600);
            if (evidenceQuote.length() < 8) throw new IllegalArgumentException("Evidence quote too short");
        }
    }

    public record Document(int schemaVersion, List<Claim> claims) {
        public Document {
            if (schemaVersion != 1 || claims == null || claims.isEmpty() || claims.size() > 100)
                throw new IllegalArgumentException("Expected ontology schema 1 and 1..100 claims");
            claims = List.copyOf(claims);
        }
    }

    public static List<Map<String, String>> definitions() {
        List<Map<String, String>> result = new ArrayList<>();
        for (Relation relation : Relation.values()) for (Type subject : Type.values()) for (Type object : Type.values()) {
            if (relation.accepts(subject, object)) result.add(Map.of(
                    "subjectType", subject.name(), "relation", relation.name(), "objectType", object.name()));
        }
        return List.copyOf(result);
    }

    private static String text(String value, int limit) {
        if (value == null || value.isBlank() || value.length() > limit || value.indexOf('\0') >= 0)
            throw new IllegalArgumentException("Invalid ontology text");
        return value.strip();
    }
}

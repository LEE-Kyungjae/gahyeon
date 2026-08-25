package com.gahyeonbot.application.privacy;

public interface SubjectDataDeletionPort {
    Layer layer();
    void delete(String serviceId, String subjectId);

    enum Layer { VECTOR, CACHE }
}

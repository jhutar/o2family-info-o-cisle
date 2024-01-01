FROM registry.fedoraproject.org/fedora-minimal 

RUN microdnf -y install python3 python3-requests \
    && microdnf clean all

COPY o2family_info.py o2family_info.py
RUN ./o2family_info.py --help

ENTRYPOINT ["./o2family_info.py"]

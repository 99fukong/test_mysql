# 使用 Python 3.10 镜像作为基础镜像
FROM python:3.8.18-slim-bullseye 

# 将工作目录设置为 /app
WORKDIR /app

RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list \
     && apt-get update --fix-missing && apt-get install -y --fix-missing \
     build-essential

#RUN apt-get update --fix-missing && apt-get install -y --fix-missing \
#    build-essential 
#    #vim

COPY ./requirements.txt /app

# RUN pip install --no-cache-dir -r requirements.txt
RUN pip install -r requirements.txt -i https://mirrors.cloud.tencent.com/pypi/simple

# Expose the port of the container
EXPOSE 9000

# Copy all files in the current directory to /app
COPY . /app


# 运行脚本
# CMD ["bash", "-c", "memoflow/cmd/run.sh"]
# CMD ["bash", "tail", "-f", "/dev/null"]
CMD ["tail", "-f", "/dev/null"] 

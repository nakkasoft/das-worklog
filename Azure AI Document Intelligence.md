MS Azure의 Document Intelligence는 문서에서 텍스트, 구조, 주요 정보를 자동으로 추출하여 처리하는 AI 서비스인 'Azure AI Document Intelligence'를 의미합니다. 
이 서비스는 기존에 'Azure AI Form Recognizer'로 불렸으나, 2023년 7월에 명칭이 변경되었습니다.

주요 기능
Azure AI Document Intelligence는 문서 처리 자동화에 필요한 다양한 기능을 제공합니다. 
광학 문자 인식(OCR): 이미지나 PDF 파일에서 인쇄된 텍스트와 필기 텍스트를 정확하게 추출합니다.
레이아웃 분석: 문서의 구조(단락, 제목, 테이블, 선택 표시 등)를 감지하고 추출합니다.
사전 구축된 모델: 영수증, 송장, 명함, 신분증 등 자주 사용되는 문서 유형에 대한 전용 모델을 제공하여 바로 사용할 수 있습니다.
사용자 지정 모델: 특정 비즈니스 문서에 맞춰 맞춤형 모델을 훈련하고 구축할 수 있습니다. 템플릿 모델과 신경망 모델을 활용할 수 있습니다.
쿼리 필드 추출: 특정 정보에 대한 자연어 쿼리를 사용하여 문서에서 특정 필드를 추출할 수 있습니다.
문서 분류: 여러 유형의 문서를 자동으로 식별하고 분류합니다. 

이점
자동화된 데이터 처리: 수동으로 문서를 입력하는 작업을 자동화하여 처리 속도와 정확성을 높여줍니다.
데이터 기반 의사결정: 추출된 정보를 구조화된 데이터로 변환하여 분석 및 시각화에 활용할 수 있습니다.
향상된 검색 기능: 문서에서 추출한 텍스트를 검색 가능하게 만들어 필요한 정보를 빠르게 찾을 수 있도록 돕습니다.
유연한 배포: 클라우드 기반 서비스뿐만 아니라 온프레미스 환경에서도 활용할 수 있습니다. 

활용 사례
금융 서비스: 대출 신청서, 보험 청구서, 거래 내역서 등 금융 문서를 자동 처리.
공급망 관리: 송장, 구매 주문서 등을 자동 처리하여 워크플로 효율화.
공공 부문: 신분증, 세금 양식 등 정부 문서를 신속하게 처리.
헬스케어: 의료 기록, 보험 카드 등 의료 문서를 분석. 

시작하는 방법
Azure AI Document Intelligence를 사용하려면 'Document Intelligence Studio'라는 온라인 도구를 활용하면 편리합니다. 코드를 작성하지 않고도 시각적인 환경에서 다양한 모델을 실험하고 사용자 지정 모델을 학습시킬 수 있습니다. 

How to use Azure AI Document Intelligence:
To use Azure Document Intelligence, first create an Azure Document Intelligence resource in the Azure portal by selecting your subscription and region. 
Then, use the Document Intelligence Studio, a web-based tool for training custom models and analyzing documents with prebuilt models. 
For programmatic use, obtain the resource's endpoint and key from the Azure portal to connect your application with the service using the client library or REST API to extract data from various document types. 

1. Create an Azure Document Intelligence Resource
Sign in to the Azure portal and search for "Document Intelligence" or navigate to "All services" > "Azure AI services". 
Create a new resource by selecting your subscription, resource group, region, and providing a unique name. 
Choose a pricing tier; a free tier is available for testing before upgrading to a standard paid tier for production use. 
Complete the creation process and then go to the resource to find your API keys and endpoint. 

2. Use the Document Intelligence Studio (No-Code)
Navigate to the Document Intelligence Studio: from your resource's overview page. 
Select a prebuilt or custom model: to analyze documents, such as invoices, receipts, or tax forms. 
Upload a sample document: or provide a URL to analyze it with the chosen model. 
Review the analysis results, which show extracted text, fields, and tables, and use the studio to train your own custom models. 

3. Integrate into Your Application (Programmatic) 
Install the Document Intelligence client library: for your preferred programming language (e.g., C#, Java, Python).
Use the endpoint and API key: obtained from your resource to create a document analysis client in your code.
Load your document: (from a file or URL).
Perform the analysis: using the client, which returns structured data including pages, lines, words, and bounding boxes.
Extract specific information: such as vendor names, customer names, and invoice totals from the analysis results.
